import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import yfinance as yf
import schedule
import time
from database_setup import create_db, insert_data, prune_old_data, update_top_stocks

DB_FILE = "stocks.db"
RISK_FREE_RATE = 0.0436 / 252  # 4.36% 1-month Treasury bill rate, divided by 252 trading days to get daily rate

# Define your tickers
stock_list = [
    "AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "NVDA", "META",
    "JPM", "V", "MA", "UNH", "HD", "DIS", "ADBE", "NFLX",
    "BAC", "INTC", "KO", "PEP", "CSCO"
]

# Function to plot stock data
def plot_stock_data(tickers):
    conn = sqlite3.connect(DB_FILE)
    
    for ticker in tickers:
        print(f"Generating graph for {ticker}...")

        # Fetch last month's stock data for the ticker
        c = conn.cursor()
        c.execute('''
            SELECT datetime, close
            FROM stock_data
            WHERE ticker = ?
            ORDER BY datetime DESC
            LIMIT 30  -- Last 30 days
        ''', (ticker,))
        data = c.fetchall()
        
        if len(data) == 0:
            print(f"No data available for {ticker}. Skipping...")
            continue
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data, columns=['datetime', 'close'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        # Plot the closing prices
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['close'], label=f'{ticker} Closing Price', color='blue')
        plt.title(f'{ticker} - Stock Price Over the Last Month')
        plt.xlabel('Date')
        plt.ylabel('Price (USD)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    conn.close()

# Initial 1-month daily data
def fetch_initial_data(tickers):
    for ticker in tickers:
        print(f"Fetching initial daily data for {ticker}")
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo", interval="1h")
        if not df.empty:
            insert_data(ticker, df)

# Hourly updates
def fetch_hourly_data(tickers):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] Fetching hourly updates...")
    for ticker in tickers:
        print(f"  > {ticker}")
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="1h")
        if not df.empty:
            df = df[df.index <= pd.Timestamp.now()]
            insert_data(ticker, df)
    prune_old_data()
    update_top_stocks()


# Run scheduler every hour
def run_scheduler():
    schedule.every().hour.at(":00").do(fetch_hourly_data, tickers=stock_list)
    while True:
        schedule.run_pending()
        time.sleep(30)

# Main program
if __name__ == "__main__":
    create_db()
    fetch_initial_data(stock_list)
    plot_stock_data(stock_list)  # Generate graph after initial data
    run_scheduler()
