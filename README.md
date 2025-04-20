# COP-4710
In this project we are building a website that tracks montly data of 20 stocks and updates it every hour and allows you to pick some stock and shows the top 5 stocks based on the sharpe ratio.

## How to Launch the Web Application

### Step 1: Install Python (if not already installed)

### Step 2: Navigate to the project folder in Terminal:
cd Downloads/COP-4710-2  # (or wherever you extracted the files)

### Step 3: Install all required packages:
pip install pandas numpy matplotlib yfinance flask flask-sqlalchemy schedule

### Step 4: Run the App
In the same Terminal, type: python app.py
Wait until you see: * Running on http://127.0.0.1:5000

### Step 5: Open the App in Your Browser
Open your web browser (Chrome, Firefox, etc.).

Type this in the address bar:

http://127.0.0.1:5000
The Stock Tracker app should now be running!

## Troubleshooting
If you get a "Module Not Found" error:
Run pip install <missing-module-name> (e.g., pip install yfinance).

If the app crashes:
Delete stocks.db (if it exists) and restart the app (python app.py).

## How to Close the App
Go back to the Terminal.

Press Ctrl + C to stop the server.
