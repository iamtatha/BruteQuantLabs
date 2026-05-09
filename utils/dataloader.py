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




prices_dir = "database/historical_data_yf"


def load_prices(stock="TCS", years=None, days=None):
    file_path = f"{prices_dir}/{stock}.NS_yf.json"
    df = pd.read_json(file_path).T

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