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

    try:
        start_date = dates[start_date_ind]
        end_date = dates[end_date_ind]
    except IndexError:
        logger.error(f"IndexError for lot {lot}. start_date_ind: {start_date_ind}, end_date_ind: {end_date_ind}, n: {n}")
        logger.error(f"Dates list: start: {dates[:3]}, end: {dates[:-3]}")
        return None
        

    _df = df[start_date:end_date]

    if log:
        print(start_date, end_date)
        print(_df)

    if _df.empty:
        print("⚠️ Empty dataframe. Check date slicing.")
        print(start_date, end_date)
        return None

    candle = detect_candles_claude(_df)
    
    if log:
        print(candle.columns)
    
    return plot_valid_signals(candle, conf_threshold)



def generate_pdf(df, dates, num_lots, stock_code, lot_size=200, conf_threshold=0.5):
    file_path_nifty_50 = f"research_candle_stick/candle_stick_examples/nifty_50/{stock_code}.pdf"
    file_path_nifty_450 = f"research_candle_stick/candle_stick_examples/nifty_450/{stock_code}.pdf"
    file_path_nifty_other = f"research_candle_stick/candle_stick_examples/nifty_other/{stock_code}.pdf"

    file_path = file_path_nifty_50
    if os.path.exists(file_path):
        logger.info(f"PDF already exists for {stock_code} in nifty_50. Skipping...")
        return
    
    file_path = file_path_nifty_450
    if os.path.exists(file_path):
        logger.info(f"PDF already exists for {stock_code} in nifty_450. Skipping...")
        return
    
    file_path = file_path_nifty_other
    if os.path.exists(file_path):
        logger.info(f"PDF already exists for {stock_code} in nifty_other. Skipping...")
        return

    with PdfPages(file_path) as pdf:
        for lot in range(num_lots):
            fig = analysis(df, dates, lot, lot_size, conf_threshold=conf_threshold)   # your function returns mplfinance fig

            if fig is None:
                logger.info(f"Empty figure for lot {lot} in {stock_code}. Finishing...")
                return

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
        print("="*100)
        logger.info(f"Generating PDF for {stock_code} | \t\t STARTING {nifty_list_tickers.index(stock_code)+1}/{len(nifty_list_tickers)}")
        run_example(stock_code)



num_lots = 50
stock_code = "TCS"
# run_example(stock_code)


run_nifty(500)
