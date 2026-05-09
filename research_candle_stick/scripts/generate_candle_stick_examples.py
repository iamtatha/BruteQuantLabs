from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import os
import sys
from pathlib import Path
import csv
import pandas as pd
import logging
import time

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


from analysis_scripts.utils.support_resistance import (
    detect_support_resistance_claude,
    plot_support_resistance,
    detect_support_resistance_walkforward,
    detect_support_resistance_walkforward_optimized,
    plot_support_resistance_compact,
    plot_support_resistance_enhanced,
)
from analysis_scripts.utils.candles import detect_candles_claude, plot_valid_signals




PRICES_DIR = "database/historical_data_yf"


def load_data(stock_code="TCS"):
    file_path = f"{PRICES_DIR}/{stock_code}.NS_yf.json"
    try:
        df = pd.read_json(file_path).T
    except FileNotFoundError:
        logger.error(f"File not found for {stock_code} at {file_path}")
        return None, None, None
    
    dates = pd.to_datetime(df.index.tolist()).tolist()
    
    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock_code}.NS", '').lower() for c in cols]
    df.columns = cols
    return df, dates, cols




def candle_stick_analysis(df, dates, lot=0, lot_size=200, log=0, conf_threshold=0.5):
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

    candle_df = detect_candles_claude(_df)
    
    if log:
        print(candle_df.columns)

    return candle_df



def support_resistance_analysis(df, dates, lot=0, lot_size=200, log=0, conf_threshold=0.5):
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
        return None, None, None
        

    _df = df[start_date:end_date]

    if log:
        print(start_date, end_date)
        print(_df)

    if _df.empty:
        print("⚠️ Empty dataframe. Check date slicing.")
        print(start_date, end_date)
        return None, None, None

    # support, resistance, _df = detect_support_resistance_walkforward(_df)
    support, resistance, _df = detect_support_resistance_walkforward_optimized(_df)

    
    if log:
        print(support.columns)
        print(resistance.columns)

    return _df, support, resistance



def get_combined_image(df, dates, lot=0, lot_size=200, log=0, conf_threshold=0.5):
    support_resistance_df, support, resistance = support_resistance_analysis(df, dates, lot, lot_size, conf_threshold=conf_threshold)
    candle_df = candle_stick_analysis(df, dates, lot, lot_size, conf_threshold=conf_threshold)

    if support_resistance_df is None or candle_df is None:
        return None

    candle_fig, _axlist = plot_valid_signals(
        candle_df, conf_threshold=0.5, fig=None, axlist=None
    )
    fig, axlist = plot_support_resistance_enhanced(support_resistance_df, support, resistance, fig=candle_fig, axlist=_axlist)
    return fig





def generate_pdf(df, dates, num_lots, stock_code, lot_size=200, conf_threshold=0.5, sub_folder="other"):
    file_path = f"research_candle_stick/candle_stick_examples/{sub_folder}/{stock_code}.pdf"

    if os.path.exists(file_path):
        logger.info(f"PDF already exists for {stock_code} in {sub_folder}. Skipping...")
        return
    

    with PdfPages(file_path) as pdf:
        for lot in range(num_lots):
            fig = get_combined_image(df, dates, lot, lot_size, conf_threshold=conf_threshold)   # your function returns mplfinance fig

            if fig is None:
                logger.info(f"Empty figure for lot {lot} in {stock_code}. Finishing...")
                return

            pdf.savefig(fig)   # add page
            fig.clf()          # clear memory (important for loops)
            plt.close(fig)

            if (lot/num_lots) % 0.2 == 0:
                logger.info(f"Generated {lot}/{num_lots} pages for {stock_code}")



def run_example(stock_code, sub_folder):
    df, dates, _ = load_data(stock_code)
    if df is None:
        logger.error(f"Data loading failed for {stock_code}. Skipping PDF generation.")
        return
    generate_pdf(df, dates, num_lots, stock_code, sub_folder=sub_folder)



def get_nifty_list(v):
    if v == 50:
        nifty_list = pd.read_csv(f"database/static_data/nifty_{v}.csv")
        nifty_list_tickers = nifty_list["Symbol"].tolist()
    elif v == 450:
        nifty_list = pd.read_csv(f"database/static_data/nifty_500.csv")
        nifty_list_500 = nifty_list["Symbol"].tolist()
        nifty_list_50 = get_nifty_list(50)
        
        nifty_list_tickers = []
        for ticker in nifty_list_500:
            if ticker not in nifty_list_50:
                nifty_list_tickers.append(ticker)

    return nifty_list_tickers



# stock_code = "TCS"
# num_lots = 5
# sub_folder = "nifty_other"
# start_time = time.time()
# run_example(stock_code, sub_folder=sub_folder)
# end_time = time.time()

# print(f"Time taken for {stock_code}: {end_time - start_time:.2f} seconds")




# stock_code = "ITC"
# num_lots = 10
# sub_folder = "nifty_other"
# start_time = time.time()
# run_example(stock_code, sub_folder=sub_folder)
# end_time = time.time()

# print(f"Time taken for {stock_code}: {end_time - start_time:.2f} seconds")













num_lots = 50
sub_folder="nifty_50"
# sub_folder="other"

v = 50


nifty_list_tickers = get_nifty_list(v)

for stock_code in nifty_list_tickers:
    print("="*100)
    logger.info(f"Generating PDF for {stock_code} | \t\t STARTING {nifty_list_tickers.index(stock_code)+1}/{len(nifty_list_tickers)}")
    run_example(stock_code, sub_folder=sub_folder)
