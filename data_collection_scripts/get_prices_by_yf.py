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
# tickers = ["HDFCBANK.NS"]
# tickers= ["ACC.NS", "TCS.NS"]

# period = "1mo"
# interval = "1d"

# fetch_or_load_stock_price(
#     tickers=tickers,
#     period=period,
#     interval=interval
# )




period = "max"
interval = "1d"


def nifty_list(v=50):
    nifty_list = pd.read_csv(f"database/csv_data/nifty_{v}.csv")

    nifty_list_tickers = nifty_list["YF_TICKER"].tolist()
    print(f"nifty_{v}_tickers: {nifty_list_tickers}")
    return nifty_list_tickers



nifty_list_tickers = nifty_list(500)
fetch_or_load_stock_price(
    tickers=nifty_list_tickers,
    period=period,
    interval=interval
)

