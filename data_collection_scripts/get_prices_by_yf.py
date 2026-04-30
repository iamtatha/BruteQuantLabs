import sys
from pathlib import Path
import csv
import pandas as pd

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_collection_scripts.utils.yf import fetch_or_load_stock_price


# tickers= ["RELIANCE.NS", "ITC.NS"]
# tickers= ["TCS.NS"]
# tickers = ["HDFCBANK.NS"]

period = "max"
interval = "1d"


nifty_50 = pd.read_csv("database/csv_data/nifty_50.csv")
# print(nifty_50.head())

nifty_50_tickers = nifty_50["YF_TICKER"].tolist()
print(nifty_50_tickers)


fetch_or_load_stock_price(
    tickers=nifty_50_tickers,
    period=period,
    interval=interval
)

