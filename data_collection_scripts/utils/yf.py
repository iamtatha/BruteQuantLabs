import yfinance as yf
import pandas as pd
import time
from typing import List, Union, Optional
import os
import sys
import json
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sqlite3

import tempfile



# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)



def load_latest_dates(meta_path: Path):
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                return json.load(f)
        except:
            logger.error(f"Error loading latest dates from {meta_path}")
            return {}
    return {}


def save_latest_dates(meta_path: Path, data: dict):
    with open(meta_path, "w") as f:
        json.dump(data, f, indent=2)


def get_last_valid_date(df):
    if df.empty:
        return None
    price_cols = [c for c in df.columns if any(x in c for x in ["Open","High","Low","Close"])]
    df = df.dropna(subset=price_cols, how="all")
    return df.index.max() if not df.empty else None




def fetch_stock_data(
    tickers: Union[str, List[str]],
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: str = "max",
    interval: str = "1d",
    group_by: str = "column",
    auto_adjust: bool = True,
    prepost: bool = False,
    threads: bool = False,
    proxy: Optional[str] = None,
    rounding: bool = False,
    timeout: int = 30,
    retries: int = 3,
    pause: float = 1.0,
    show_errors: bool = True,
) -> pd.DataFrame:
    """
    Fetch stock data using yfinance with retries and flexible arguments.

    Args:
        tickers: str or list of tickers
        start, end: date range (YYYY-MM-DD)
        period: '1d','5d','1mo','1y','max', etc.
        interval: '1m','5m','1d','1wk','1mo', etc.
        group_by: 'column' or 'ticker'
        auto_adjust: adjust OHLC for splits/dividends
        prepost: include pre/post market data
        threads: use multithreading
        proxy: proxy URL if needed
        rounding: round values
        timeout: request timeout
        retries: retry attempts
        pause: delay between retries
        show_errors: print errors or not

    Returns:
        pandas DataFrame
    """
    logger.info(f"Fetching data for {tickers} | start={start} end={end} period={period} interval={interval}")

    for attempt in range(retries):
        try:
            df = yf.download(
                tickers=tickers,
                start=start,
                end=end,
                period=period if start is None else None,
                interval=interval,
                group_by=group_by,
                auto_adjust=auto_adjust,
                prepost=prepost,
                threads=threads,
                rounding=rounding,
                timeout=timeout,
                progress=False,
            )

            if df is None or df.empty:
                raise ValueError("Empty data returned")

            return df

        except Exception as e:
            if show_errors:
                print(f"[Attempt {attempt+1}] Error: {e}")

            time.sleep(pause)

    raise Exception("Failed after retries")















# ----------------------------
# Helpers
# ----------------------------
def safe_json_dump(data, file_path):
    dir_name = os.path.dirname(file_path)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name) as tmp:
        json.dump(data, tmp)
        temp_name = tmp.name
    os.replace(temp_name, file_path)


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # ---- Normalize columns ----
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(x) for x in col if x]) for col in df.columns]
    else:
        df.columns = [
            "_".join(col) if isinstance(col, tuple) else str(col)
            for col in df.columns
        ]

    # ---- Normalize index ----
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]

    return df


def load_json_df(file_path):
    if not os.path.exists(file_path):
        return pd.DataFrame()

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data).T
        return normalize_df(df)
    except json.JSONDecodeError:
        logger.error(f"Corrupted JSON → deleting: {file_path}")
        os.remove(file_path)
        return pd.DataFrame()
    except Exception as e:
        logger.warning(f"Load failed: {e}")
        return pd.DataFrame()


def get_last_valid_date(df):
    if df.empty:
        return None

    # price columns only
    price_cols = [c for c in df.columns if any(x in c for x in ["Open","High","Low","Close"])]

    # drop rows where ALL prices are NaN
    valid_df = df.dropna(subset=price_cols, how="all")

    if valid_df.empty:
        return None

    return valid_df.index.max()





# ----------------------------
# MAIN FUNCTION
# ----------------------------
def fetch_or_load_stock_price(
    tickers: Union[str, List[str]],
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: str = "max",
    interval: str = "1d",
    group_by: str = "column",
    auto_adjust: bool = True,
    prepost: bool = False,
    threads: bool = False,
    proxy: Optional[str] = None,
    rounding: bool = False,
    timeout: int = 30,
    retries: int = 3,
    pause: float = 1.0,
    show_errors: bool = True,
    folder: str = "database/historical_data_yf",
) -> pd.DataFrame:

    os.makedirs(folder, exist_ok=True)

    if isinstance(tickers, str):
        tickers = [tickers]

    final_data = {}
    today = pd.Timestamp.today().normalize()

    for ticker in tickers:
        logger.info(f"Processing {ticker}")

        file_path = os.path.join(folder, f"{ticker}_yf.json")

        # ----------------------------
        # Load existing
        # ----------------------------
        existing_df = load_json_df(file_path)
        logger.info(f"{ticker}: existing rows = {len(existing_df)}")

        # ----------------------------
        # Find last valid date
        # ----------------------------
        last_date = get_last_valid_date(existing_df)

        if last_date is not None:
            if last_date.normalize() >= today:
                logger.info(f"{ticker}: Already up-to-date → skipping")
                final_data[ticker] = existing_df
                continue

            fetch_start = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"{ticker}: incremental fetch from {fetch_start}")
        else:
            fetch_start = start
            logger.info(f"{ticker}: full fetch")

        # ----------------------------
        # Fetch new data
        # ----------------------------
        try:
            new_df = fetch_stock_data(
                ticker,
                start=fetch_start,
                end=end,
                period=period if last_date is None else None,
                interval=interval,
                group_by=group_by,
                auto_adjust=auto_adjust,
                prepost=prepost,
                threads=threads,
                proxy=proxy,
                rounding=rounding,
                timeout=timeout,
                retries=retries,
                pause=pause,
                show_errors=show_errors,
            )
        except Exception as e:
            logger.error(f"{ticker}: fetch failed → {e}")
            final_data[ticker] = existing_df
            continue

        new_df = normalize_df(new_df)
        logger.info(f"{ticker}: fetched rows = {len(new_df)}")

        # ----------------------------
        # Merge (APPEND, not overwrite)
        # ----------------------------
        combined_df = pd.concat([existing_df, new_df])

        if not combined_df.empty:
            combined_df = normalize_df(combined_df)
            combined_df = combined_df[~combined_df.index.duplicated(keep="last")]
            combined_df.sort_index(inplace=True)

        logger.info(f"{ticker}: total rows after merge = {len(combined_df)}")

        # ----------------------------
        # Save (safe + append preserved)
        # ----------------------------
        if not combined_df.empty:
            df_save = combined_df.copy()

            # Convert index to string
            df_save.index = df_save.index.strftime("%Y-%m-%d")

            # NaN → None
            df_save = df_save.where(pd.notna(df_save), None)

            safe_json_dump(df_save.to_dict(orient="index"), file_path)

            logger.info(f"{ticker}: saved successfully")


            df_save = df_save.reset_index().rename(columns={"index": "Date"})
            rename_map = {}
            for col in df_save.columns:
                if "Close" in col:
                    rename_map[col] = "close"
                elif "High" in col:
                    rename_map[col] = "high"
                elif "Low" in col:
                    rename_map[col] = "low"
                elif "Open" in col:
                    rename_map[col] = "open"
                elif "Volume" in col:
                    rename_map[col] = "volume"
            df_save = df_save.rename(columns=rename_map)

            conn = sqlite3.connect("database/bql_stock_prices.db")
            df_save.to_sql(ticker.replace('.NS', ''), conn, if_exists="append", index=False)
            conn.close()
            logger.info(f"Appended data to SQLite database")


        final_data[ticker] = combined_df

    # ----------------------------
    # Return
    # ----------------------------



    if len(final_data) == 1:
        return list(final_data.values())[0]









