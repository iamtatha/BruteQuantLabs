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
    nifty_list = pd.read_csv(f"database/static_data/nifty_{v}.csv")

    nifty_list_tickers = nifty_list["YF_TICKER"].tolist()
    print(f"nifty_{v}_tickers: {nifty_list_tickers}")
    return nifty_list_tickers


def get_all_nifty_tickers():
    nifty_other_list = pd.read_csv(f"database/static_data/nse_equity_list.csv")
    symbols = nifty_other_list["SYMBOL"].tolist()
    tickers = [f"{symbol}.NS" for symbol in symbols]

    nifty_500_list = nifty_list(v=500)

    ret_list = []
    for ticker in tickers:
        if ticker not in nifty_500_list:
            ret_list.append(ticker)
    return ret_list



non_nifty_500 = get_all_nifty_tickers()


fetch_or_load_stock_price(
    tickers=non_nifty_500,
    period=period,
    interval=interval
)

