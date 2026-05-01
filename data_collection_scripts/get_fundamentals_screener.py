import sys
from pathlib import Path
import csv
import pandas as pd

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_collection_scripts.utils.screener import ScreenerScraper




def nifty_list(v=50):
    nifty_list = pd.read_csv(f"database/csv_data/nifty_{v}.csv")

    nifty_list_tickers = nifty_list["Symbol"].tolist()
    print(f"nifty_{v}_tickers: {nifty_list_tickers}")
    return nifty_list_tickers



nifty_list_tickers = nifty_list(50)

scraper = ScreenerScraper(headless=False, data_dir=ROOT_DIR / "database" / "fundamentals_data")

stocks = nifty_list_tickers
results = scraper.batch_scrape(stocks, delay_between=2.0)

# Summary
success = sum(1 for v in results.values() if v is not None)
print(f"\n{'='*50}")
print(f"Scraped {success}/{len(stocks)} stocks successfully")
print(f"Data saved to: {scraper.data_dir}")

scraper.close()



