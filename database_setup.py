import sqlite3
import numpy as np
import pandas as pd
import yfinance as yf 
from datetime import datetime, timedelta

DB_FILE = "stocks.db"
RISK_FREE_RATE = 0.0436 / 252  # 4.36% 1-month Treasury bill rate, divided by 252 trading days to get daily rate

def create_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS stock_data (
            ticker TEXT,
            datetime TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, datetime)
        )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS watched_stocks (
        ticker TEXT PRIMARY KEY
    )
 ''')


    c.execute('''
    CREATE TABLE IF NOT EXISTS bottom_stocks (
        rank INTEGER,
        ticker TEXT,
        sharpe_ratio REAL,
        datetime TEXT
    )
 ''')

    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_datetime ON stock_data(datetime)
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS top_stocks (
            rank INTEGER,
            ticker TEXT,
            sharpe_ratio REAL,
            datetime TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
def insert_data(ticker, df):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for index, row in df.iterrows():
        try:
            c.execute('''
                INSERT OR IGNORE INTO stock_data (ticker, datetime, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker,
                index.strftime('%Y-%m-%d %H:%M:%S'),
                row['Open'],
                row['High'],
                row['Low'],
                row['Close'],
                row['Volume']
            ))
        except Exception as e:
            print(f"Error inserting {ticker} @ {index}: {e}")
    conn.commit()
    conn.close()

def prune_old_data():
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM stock_data WHERE datetime < ?", (cutoff,))
    conn.commit()
    conn.close()
    


def calculate_sharpe_ratio(ticker):
    # Fetch stock data 
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT datetime, close
        FROM stock_data
        WHERE ticker = ?
        ORDER BY datetime DESC
        LIMIT 30 
    ''', (ticker,))
    data = c.fetchall()

    if len(data) < 2:
        conn.close()
        return None  

    # Convert to pandas DataFrame for easier manipulation
    df = pd.DataFrame(data, columns=['datetime', 'close'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    
    # Calculate daily returns
    df['30h_return'] = df['close'].pct_change()

    # Calculate Sharpe ratio (mean return - risk-free rate) / std deviation of returns
    mean_return = df['30h_return'].mean()
    std_dev = df['30h_return'].std()

    sharpe_ratio = (mean_return - RISK_FREE_RATE) / std_dev if std_dev != 0 else 0
    conn.close()
    return sharpe_ratio

def update_top_stocks():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Get the most recent timestamp
    c.execute('''
        SELECT DISTINCT datetime FROM stock_data
        ORDER BY datetime DESC
        LIMIT 1
    ''')
    latest_time = c.fetchone()[0]

    # Get list of all tickers
    c.execute('SELECT DISTINCT ticker FROM stock_data')
    tickers = [row[0] for row in c.fetchall()]

    # Calculate Sharpe ratio for each ticker
    sharpe_ratios = []
    for ticker in tickers:
        sharpe_ratio = calculate_sharpe_ratio(ticker)
        if sharpe_ratio is not None:
            sharpe_ratios.append((ticker, sharpe_ratio))

    # Sort stocks by Sharpe ratio in descending order
    top_stocks = sorted(sharpe_ratios, key=lambda x: x[1], reverse=True)[:5]

    # Clear old top_stocks
    c.execute('DELETE FROM top_stocks')

    # Insert new top 5
    for rank, (ticker, sharpe_ratio) in enumerate(top_stocks, start=1):
        c.execute('''
            INSERT INTO top_stocks (rank, ticker, sharpe_ratio, datetime)
            VALUES (?, ?, ?, ?)
        ''', (rank, ticker, sharpe_ratio, latest_time))

         # Insert bottom 5
    c.execute('DELETE FROM bottom_stocks')

    bottom_stocks = sorted(sharpe_ratios, key=lambda x: x[1])[:5]  # Ascending order = worst Sharpe ratios

    for rank, (ticker, sharpe_ratio) in enumerate(bottom_stocks, start=1):
        c.execute('''
            INSERT INTO bottom_stocks (rank, ticker, sharpe_ratio, datetime)
            VALUES (?, ?, ?, ?)
        ''', (rank, ticker, sharpe_ratio, latest_time))

    conn.commit()
    conn.close()

def add_to_watchlist(ticker):
    ticker = ticker.upper().strip()
    # Check if it's a valid ticker using yfinance
    stock = yf.Ticker(ticker)
    try:
        test_data = stock.history(period="1d")
        if test_data.empty:
            print(f"Ticker '{ticker}' is not valid or has no data.")
            return False
    except Exception as e:
        print(f"Error checking ticker '{ticker}': {e}")
        return False

    # Add to database
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO watched_stocks (ticker) VALUES (?)', (ticker,))
        conn.commit()
        print(f"✅ '{ticker}' added to watchlist.")
    except Exception as e:
        print(f"Error inserting '{ticker}' into watchlist: {e}")
        return False
    finally:
        conn.close()

    return True

def remove_from_watchlist(ticker):
    ticker = ticker.upper().strip()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('DELETE FROM watched_stocks WHERE ticker = ?', (ticker,))
        conn.commit()
        print(f"❌ '{ticker}' removed from watchlist.")
        return True
    except Exception as e:
        print(f"Error removing '{ticker}' from watchlist: {e}")
        return False
    finally:
        conn.close()

def add_company_info(ticker, company_name, sector=None, industry=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_info (
            ticker TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            industry TEXT
        )
    ''')
    
    # Insert or update company info
    c.execute('''
        INSERT OR REPLACE INTO company_info (ticker, company_name, sector, industry)
        VALUES (?, ?, ?, ?)
    ''', (ticker, company_name, sector, industry))
    
    conn.commit()
    conn.close()

def get_company_info(ticker):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('SELECT * FROM company_info WHERE ticker = ?', (ticker,))
    info = c.fetchone()
    
    conn.close()
    return info
