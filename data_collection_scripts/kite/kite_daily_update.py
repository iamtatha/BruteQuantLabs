"""
STEP 2: Daily incremental updater
Run this every evening after 4 PM (market close) to append today's OHLCV
to your existing Parquet files.

Schedule with cron:
  0 16 * * 1-5  /usr/bin/python3 /path/to/kite_daily_update.py
  (Mon–Fri at 4 PM IST)
"""

import os
import time
import logging
import datetime
import pandas as pd
from kiteconnect import KiteConnect

# ─────────────────────────────────────────────
# CONFIG — keep in sync with backfill script
# ─────────────────────────────────────────────
from dotenv import load_dotenv
import os
load_dotenv()

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
TOKEN_FILE = "./data/access_token.txt"
DATA_DIR     = "./data/historical"
RATE_LIMIT_DELAY = 0.35

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

NIFTY50_SYMBOLS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BEL",
    "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK",
    "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SHRIRAMFIN", "SBIN",
    "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]


def init_kite() -> KiteConnect:
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    return kite


def build_instrument_map(kite: KiteConnect) -> dict[str, int]:
    instruments = kite.instruments("NSE")
    return {
        inst["tradingsymbol"]: inst["instrument_token"]
        for inst in instruments
        if inst["tradingsymbol"] in NIFTY50_SYMBOLS and inst["instrument_type"] == "EQ"
    }


def is_trading_day(date: datetime.date) -> bool:
    """Skip weekends. Does not account for holidays — extend with NSE holiday list if needed."""
    return date.weekday() < 5  # Mon=0 ... Fri=4


def update_symbol(kite, symbol, token):
    path = os.path.join(DATA_DIR, f"{symbol}.parquet")

    if not os.path.exists(path):
        log.warning(f"  {symbol}: no existing file — run backfill first")
        return

    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    last_date = df["timestamp"].max().date()
    today     = datetime.date.today()

    if last_date >= today:
        log.info(f"  {symbol}: already current ({last_date})")
        return

    from_date = last_date + datetime.timedelta(days=1)

    try:
        candles = kite.historical_data(
            instrument_token=token,
            from_date=from_date,
            to_date=today,
            interval="day",
        )
        if not candles:
            log.info(f"  {symbol}: no new candles (holiday or weekend)")
            return

        new_df = pd.DataFrame(candles).rename(columns={"date": "timestamp"})
        new_df["timestamp"] = pd.to_datetime(new_df["timestamp"])
        new_df = new_df[["timestamp", "open", "high", "low", "close", "volume"]]

        combined = pd.concat([df, new_df], ignore_index=True)
        combined.drop_duplicates(subset=["timestamp"], inplace=True)
        combined.sort_values("timestamp", inplace=True)
        combined.to_parquet(path, index=False)

        log.info(f"  {symbol}: +{len(new_df)} rows → total {len(combined)}")
        time.sleep(RATE_LIMIT_DELAY)

    except Exception as e:
        log.error(f"  {symbol}: ERROR — {e}")


def main():
    today = datetime.date.today()
    if not is_trading_day(today):
        log.info(f"Today ({today}) is not a trading day. Exiting.")
        return

    log.info(f"Daily update — {today}")
    kite    = init_kite()
    tok_map = build_instrument_map(kite)

    for i, (symbol, token) in enumerate(tok_map.items(), 1):
        log.info(f"[{i}/{len(tok_map)}] {symbol}")
        update_symbol(kite, symbol, token)

    log.info("✅ Daily update complete.")


if __name__ == "__main__":
    main()
