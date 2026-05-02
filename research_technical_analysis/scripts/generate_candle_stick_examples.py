from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import os
import sys
from pathlib import Path
import csv
import pandas as pd
import logging

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('screener_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


from analysis_scripts.utils.candles import detect_candles_claude, plot_valid_signals




PRICES_DIR = "database/historical_data_yf"


def load_data(stock_code="TCS"):
    file_path = f"{PRICES_DIR}/{stock_code}.NS_yf.json"
    df = pd.read_json(file_path).T
    
    dates = pd.to_datetime(df.index.tolist()).tolist()
    
    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock_code}.NS", '').lower() for c in cols]
    df.columns = cols
    return df, dates, cols




def analysis(df, dates, lot=0, lot_size=200, log=0, conf_threshold=0.5):
    n = len(df)

    step = 50

    start_date_ind = n - (lot_size + step * lot)
    end_date_ind = n - (step * lot) - 1

    start_date = dates[start_date_ind]
    end_date = dates[end_date_ind]

    _df = df[start_date:end_date]

    if log:
        print(start_date, end_date)
        print(_df)

    if _df.empty:
        print("⚠️ Empty dataframe. Check date slicing.")
        print(start_date, end_date)
        raise ValueError("Data slice is empty")

    candle = detect_candles_claude(_df)
    
    if log:
        print(candle.columns)
    
    return plot_valid_signals(candle, conf_threshold)



def generate_pdf(df, dates, num_lots, stock_code, lot_size=200, conf_threshold=0.5):
    print("="*100)
    logger.info(f"Generating PDF for {stock_code}")
    with PdfPages(f"research_technical_analysis/candle_stick_examples/{stock_code}.pdf") as pdf:
        for lot in range(num_lots):
            fig = analysis(df, dates, lot, lot_size, conf_threshold=conf_threshold)   # your function returns mplfinance fig

            if fig is None:
                continue

            pdf.savefig(fig)   # add page
            fig.clf()          # clear memory (important for loops)
            plt.close(fig)

            if (lot/num_lots) % 0.2 == 0:
                logger.info(f"Generated {lot}/{num_lots} pages for {stock_code}")



def run_example(stock_code):
    df, dates, _ = load_data(stock_code)
    generate_pdf(df, dates, num_lots, stock_code)



def run_nifty(v):
    nifty_list = pd.read_csv(f"database/static_data/nifty_{v}.csv")

    nifty_list_tickers = nifty_list["Symbol"].tolist()
    print(f"nifty_{v}_tickers: {nifty_list_tickers}")
    
    for stock_code in nifty_list_tickers:
        run_example(stock_code)



num_lots = 50
stock_code = "TCS"
# run_example(stock_code)


run_nifty(50)
