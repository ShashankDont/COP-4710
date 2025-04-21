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

    all_tickers = set(tickers)

    # Pull watched stocks from DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT ticker FROM watched_stocks")
    watched = [row[0] for row in c.fetchall()]
    conn.close()

    all_tickers.update(watched)  # combine static + user-entered

    for ticker in all_tickers:
        print(f"  > {ticker}")
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="1h")
        if not df.empty:
            df = df[df.index <= pd.Timestamp.now()]
            insert_data(ticker, df)

    prune_old_data()
    update_top_stocks()

