import sys
from pathlib import Path

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/strategies.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import pandas as pd
import sqlite3



prices_dir = "database/historical_data_yf"


def load_prices(stock="TCS", years=None, days=None):
    file_path = f"{prices_dir}/{stock}.NS_yf.json"
    try:
        df = pd.read_json(file_path).T
    except FileNotFoundError:
        return None, None, None

    # Convert index to datetime
    df.index = pd.to_datetime(df.index)

    # Filter data
    if years is not None:
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        df = df[df.index >= cutoff]

    if days is not None:
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]

    # Prepare outputs
    dates = df.index.tolist()

    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock}.NS", '').lower() for c in cols]
    df.columns = cols

    return df, dates, cols




def load_stock_codes_industries(v):
    DIR = "database/static_data"
    if v != 450:
        file_path = f"{DIR}/nifty_{v}.csv"
        try:
            df = pd.read_csv(file_path)
            stock_codes = df["Symbol"].tolist()
            stock_industries = {
                row["Symbol"]: row["Industry"] for _, row in df.iterrows()
            }
            print("Loaded stock codes and industries for Nifty", v)
            return stock_codes, stock_industries
        except FileNotFoundError:
            return None, None

    else:
        try:
            nifty_500_path = f"{DIR}/nifty_500.csv"
            nifty_500_list = pd.read_csv(nifty_500_path)["Symbol"].tolist()

            nifty_50_path = f"{DIR}/nifty_50.csv"
            nifty_50_list = pd.read_csv(nifty_50_path)["Symbol"].tolist()
            stock_codes = [ele for ele in nifty_500_list if ele not in nifty_50_list]
            stock_industries = {
                row["Symbol"]: row["Industry"] for _, row in df.iterrows()
            }
            print("Loaded stock codes and industries for Nifty 500 (excluding Nifty 50)")
            return stock_codes, stock_industries
        except FileNotFoundError:
            return None, None





def load_stock_summary(v="500"):
    conn = sqlite3.connect("database/bql_stock_summary.db")
    if v == 50:
        df = pd.read_sql_query("SELECT * FROM nifty_50", conn)
    else:
        df = pd.read_sql_query("SELECT * FROM nifty_500", conn)
    # Close connection
    conn.close()
    return df



def load_industry(industry="Information Technology", v=500):
    stock_summary = load_stock_summary(v)
    filtered_stocks = stock_summary[stock_summary['Industry'] == industry]
    list_stocks = filtered_stocks['Symbol'].tolist()
    return filtered_stocks, list_stocks


