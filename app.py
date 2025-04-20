from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from database_setup import add_to_watchlist, remove_from_watchlist, create_db, update_top_stocks
from program import fetch_initial_data, stock_list

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for flash messages

create_db()
fetch_initial_data([
    "AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "NVDA", "META",
    "JPM", "V", "MA", "UNH", "HD", "DIS", "ADBE", "NFLX",
    "BAC", "INTC", "KO", "PEP", "CSCO"
])
update_top_stocks()

# Database configuration
DATABASE = 'stocks.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.context_processor
def inject_common_vars():
    """Inject common variables into all templates"""
    conn = get_db_connection()
    last_update = conn.execute('SELECT datetime FROM top_stocks LIMIT 1').fetchone()
    conn.close()
    return {
        'current_year': datetime.now().year,
        'last_update': last_update['datetime'] if last_update else "Never"
    }

@app.route('/')
def index():
    conn = get_db_connection()
    
    # Get top 5 stocks
    top_stocks = conn.execute('SELECT * FROM top_stocks ORDER BY rank').fetchall()
    
    # Get bottom 5 stocks
    bottom_stocks = conn.execute('SELECT * FROM bottom_stocks ORDER BY rank').fetchall()
    
    conn.close()
    
    return render_template('index.html', 
                         top_stocks=top_stocks, 
                         bottom_stocks=bottom_stocks)

@app.route('/stocks')
def stocks():
    conn = get_db_connection()
    
    # Get all unique tickers
    tickers = conn.execute('SELECT DISTINCT ticker FROM stock_data').fetchall()
    
    conn.close()
    
    return render_template('stocks.html', tickers=tickers)

@app.route('/stock/<ticker>')
def stock_detail(ticker):
    conn = get_db_connection()
    
    # Get stock data
    stock_data = conn.execute('''
        SELECT datetime, open, high, low, close, volume 
        FROM stock_data 
        WHERE ticker = ? 
        ORDER BY datetime DESC
        LIMIT 30
    ''', (ticker,)).fetchall()
    
    conn.close()
    
    # Generate plot - use Agg backend for non-interactive plotting
    import matplotlib
    matplotlib.use('Agg')  # Set the backend before importing pyplot
    import matplotlib.pyplot as plt
    from io import BytesIO
    import base64
    
    dates = [row['datetime'] for row in stock_data]
    closes = [row['close'] for row in stock_data]
    
    plt.figure(figsize=(10, 5))
    plt.plot(dates, closes)
    plt.title(f'{ticker} Stock Price (Last 30 Days)')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save plot to a bytes buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return render_template('stock_detail.html', 
                         ticker=ticker,
                         stock_data=stock_data,
                         plot_data=plot_data)

@app.route('/watchlist', methods=['GET', 'POST'])
def watchlist():
    if request.method == 'POST':
        ticker = request.form.get('ticker', '').strip().upper()
        action = request.form.get('action')
        
        if not ticker:
            flash('Please enter a stock ticker', 'danger')
            return redirect(url_for('watchlist'))
            
        try:
            if action == 'add':
                if add_to_watchlist(ticker):
                    flash(f'{ticker} added to watchlist successfully!', 'success')
                else:
                    flash(f'Failed to add {ticker}. Please check the ticker symbol.', 'danger')
            elif action == 'remove':
                if remove_from_watchlist(ticker):
                    flash(f'{ticker} removed from watchlist successfully!', 'success')
                else:
                    flash(f'Failed to remove {ticker}.', 'danger')
        except Exception as e:
            flash(f'Error processing request: {str(e)}', 'danger')
        
        return redirect(url_for('watchlist'))
    
    conn = get_db_connection()
    watched_stocks = conn.execute('SELECT * FROM watched_stocks').fetchall()
    conn.close()
    
    return render_template('watchlist.html', watched_stocks=watched_stocks)

if __name__ == '__main__':
    app.run(debug=True)
