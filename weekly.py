import pandas as pd
import yfinance as yf
import numpy as np
import time
from bs4 import BeautifulSoup
import requests
import logging
import warnings
import sys
import os
from contextlib import redirect_stdout, redirect_stderr

# Suppress warnings and logging
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

# Disable tqdm progress bars
import os
os.environ['TQDM_DISABLE'] = '1'

def fetch_screener_data(base_url, max_pages=5):
    columns = ['S.No.', 'Symbol', 'CMP Rs.', 'P/E', 'Mar Cap Rs.Cr.', 'Div Yld %', 'NP Qtr Rs.Cr.', 'Qtr Profit Var %', 'Sales Qtr Rs.Cr.', 'Qtr Sales Var %', 'ROCE %', '1Yr return %', 'Vol 1d']
    data = pd.DataFrame()
    for page in range(1, max_pages+1):
        url = f'{base_url}?page={page}'
        # print(f'Loading Screener page: {url}')  # Commented out for cleaner output
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if not table:
                break
            rows = table.find_all('tr')
            page_data = []
            for row in rows[1:]:  # skip header
                cols = row.find_all('td')
                if len(cols) < 2:
                    continue
                name_cell = cols[1]
                link = name_cell.find('a')
                if link:
                    href = link['href']
                    symbol = href.split('/')[-2].upper()
                    row_data = [col.text.strip() for col in cols]
                    row_data[1] = symbol  # replace name with symbol
                    page_data.append(row_data)
            if page_data:
                df_page = pd.DataFrame(page_data, columns=columns)
                data = pd.concat([data, df_page], axis=0)
            if len(page_data) < 20:
                break
        except Exception as e:
            # print(f'Error reading {url}:', e)  # Commented out for cleaner output
            break
    data = data.reset_index(drop=True)
    return data

def compute_rsi(series, window=14):
    diff = series.diff()
    gain = (diff.where(diff > 0, 0)).rolling(window=window).mean()
    loss = (-diff.where(diff < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

### ---------- MAIN ----------

# Screener.in public screen URL: Use Nifty 200, Bank Nifty, or any custom screen
SCREENER_SCREEN_URL = 'https://www.screener.in/screens/764718/weekly-rebalancing-query-strategy/'   # <-- replace with any Screener screen
LOOKBACK_4W = 20
LOOKBACK_12W = 60
MIN_VOLUME = 500000
INDEX_SYMBOL = '^NSEI'

df_fund = fetch_screener_data(SCREENER_SCREEN_URL, max_pages=20)

if df_fund.empty:
    print("No data loaded from Screener. Please check the URL and ensure the screen exists and is public.")
    exit()

if 'Symbol' not in df_fund.columns:
    print("Symbol column not found in the loaded data. Available columns:", list(df_fund.columns))
    exit()

# Normalise symbol for Yahoo Finance (.NS suffix for NSE stocks)
def symbol_to_yahoo(sym):
    return str(sym).strip() + '.NS'

stock_list = df_fund['Symbol'].astype(str).apply(symbol_to_yahoo).tolist()
try:
    index = yf.download(INDEX_SYMBOL, period='16wk', interval='1d', auto_adjust=False, progress=False)['Close']
except Exception as e:
    index = None

results = []
for i, row in df_fund.iterrows():
    symbol = symbol_to_yahoo(str(row['Symbol']))
    if 'CONSOLIDATED' in symbol or '&' in symbol or symbol == 'GVT&D.NS':
        continue
    try:
        df = yf.download(symbol, period='16wk', interval='1d', auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)  # drop Ticker level

        if len(df) < LOOKBACK_12W:
            continue
        close = df['Close'].dropna().astype(float)
        volume = df['Volume'].dropna().astype(float)

        if len(close) < LOOKBACK_12W or len(volume) < LOOKBACK_4W:
            continue

        # Fetch sector from Yahoo Finance
        try:
            ticker = yf.Ticker(symbol)
            sector = ticker.info.get('sector', 'Unknown')
        except Exception as e:
            sector = 'Unknown'

        roc_4w = (close.iloc[-1] - close.iloc[-LOOKBACK_4W]) / close.iloc[-LOOKBACK_4W] * 100
        roc_12w = (close.iloc[-1] - close.iloc[-LOOKBACK_12W]) / close.iloc[-LOOKBACK_12W] * 100
        rsi = compute_rsi(close).iloc[-1]
        if index is not None:
            rel_strength = (close.iloc[-1] / close.iloc[-LOOKBACK_4W]) / (index.iloc[-1] / index.iloc[-LOOKBACK_4W])
        else:
            rel_strength = 1  # neutral relative strength
        high_breakout = close.iloc[-1] >= close.max()
        avg_vol = float(volume[-LOOKBACK_4W:].mean())

        # Quick fundamental check using Screener columns, override as needed for your screen!
        debt_to_equity = 0.0  # not available in this screen
        sales_qoq = float(row.get('Qtr Sales Var %', 0.0))
        profit_qoq = float(row.get('Qtr Profit Var %', 0.0))
        cashflow = 1  # not available

        if avg_vol < MIN_VOLUME:
            continue

        score = (roc_4w/25 + roc_12w/50 + rsi/50 + (rel_strength-1)*5 + int(high_breakout)*2)*0.4

        results.append({
            'symbol': symbol.replace('.NS',''),
            'current_price': round(close.iloc[-1],2),
            '1w_return_%': round((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]*100,1),
            'sector': sector,
            'momentum_score': round(score,2),
            'roc_4w': round(roc_4w,2),
            'key_catalyst': f"{sector}, 52-wk breakout: {high_breakout}, RSI: {round(rsi,1)}"
        })
    except Exception as e:
        pass

# Output only the final results
df_results = pd.DataFrame(results)
if not df_results.empty:
    df_results['momentum_score'] = df_results['momentum_score'].astype(float)
    df_results = df_results.dropna(subset=['momentum_score'])
    if not df_results.empty:
        df_results = df_results.sort_values(by='momentum_score', ascending=False)
        df_results['rank'] = range(1, len(df_results) + 1)
        print("****Top 10 Momentum Stocks for next week****")
        top_10 = df_results.head(10)
        for idx, row in top_10.iterrows():
            print(f"{int(row['rank'])}. {row['symbol']} : {row['momentum_score']}")
    else:
        print("No valid stocks found after filtering.")
else:
    print("No valid stocks found.")