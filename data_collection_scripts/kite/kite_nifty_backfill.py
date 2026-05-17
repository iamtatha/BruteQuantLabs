"""
STEP 1: One-time historical backfill (MULTITHREADED)
Fetches 10 years of daily OHLCV for all NSE stocks using multiple threads.

Threading model:
  - Each symbol runs in its own thread
  - Each thread has its own KiteConnect instance (thread-safe)
  - Rate limiting is shared across threads via a token bucket
  - MAX_WORKERS controls parallelism (3-5 is safe for Kite's rate limits)
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import os
import time
import logging
import datetime
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(threadName)s]  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
API_KEY      = os.getenv("KITE_API_KEY")
API_SECRET   = os.getenv("KITE_API_SECRET")
TOKEN_FILE   = "./database/raw_data/data_kite/access_token.txt"
OUTPUT_DIR   = "./database/raw_data/data_kite/historical"
YEARS_BACK   = 10
CHUNK_DAYS   = 365
INTERVAL     = "day"

# Threading config
# Kite allows ~3 requests/sec total across all threads.
# With MAX_WORKERS=3 and RATE_LIMIT_DELAY=0.35s per thread,
# you get ~3 req/sec total — safe limit.
# Increase MAX_WORKERS + RATE_LIMIT_DELAY proportionally if needed.
MAX_WORKERS      = 3      # parallel threads
RATE_LIMIT_DELAY = 1.1    # seconds between requests PER THREAD (3 threads × 1/1.1s ≈ 2.7 req/s)
ERROR_BACKOFF    = 5      # seconds to wait after a rate-limit or API error

ACCESS_TOKEN = None
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE) as f:
        ACCESS_TOKEN = f.read().strip()
        log.info(f"Loaded access token from {TOKEN_FILE}")

# ─────────────────────────────────────────────
# GLOBAL RATE LIMITER
# Token bucket: ensures total requests/sec stays within Kite's limit
# regardless of how many threads are running.
# ─────────────────────────────────────────────
class RateLimiter:
    """
    Thread-safe token bucket rate limiter.
    MAX_CALLS per PERIOD seconds across ALL threads.
    """
    def __init__(self, max_calls: int = 3, period: float = 1.0):
        self._max_calls = max_calls
        self._period    = period
        self._calls     = []
        self._lock      = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.monotonic()
            # Remove calls older than the period window
            self._calls = [t for t in self._calls if now - t < self._period]
            if len(self._calls) >= self._max_calls:
                # Sleep until the oldest call falls out of the window
                sleep_for = self._period - (now - self._calls[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
            self._calls.append(time.monotonic())

# One shared rate limiter for all threads
_rate_limiter = RateLimiter(max_calls=3, period=1.0)

# Thread-local KiteConnect instances (one per thread)
_thread_local = threading.local()

def get_kite() -> KiteConnect:
    """Returns a thread-local KiteConnect instance."""
    if not hasattr(_thread_local, "kite"):
        _thread_local.kite = KiteConnect(api_key=API_KEY)
        _thread_local.kite.set_access_token(ACCESS_TOKEN)
    return _thread_local.kite

# ─────────────────────────────────────────────
# INSTRUMENT MAP
# ─────────────────────────────────────────────
from utils.dataloader import load_stock_codes_industries
STOCK_SYMBOLS, _ = load_stock_codes_industries(v=500)

INDICES = {
    "NIFTY_50":       256265,
    "NIFTY_BANK":     260105,
    "INDIA_VIX":      264969,
    "NIFTY_IT":       259849,
    "NIFTY_MIDCAP50": 260873,
    "NIFTY_PHARMA":   262409,
    "NIFTY_FMCG":     261897,
    "NIFTY_AUTO":     263433,
    "NIFTY_METAL":    263689,
    "NIFTY_REALTY":   261129,
    "NIFTY_PSU_BANK": 262921,
    "NIFTY_100":      260617,
}


def build_instrument_map(mode="all") -> dict[str, int]:
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    log.info("Downloading NSE instrument list...")
    instruments = kite.instruments("NSE")

    if mode == "all":
        token_map = {
            inst["tradingsymbol"]: inst["instrument_token"]
            for inst in instruments
            if inst["instrument_type"] == "EQ" and inst["segment"] == "NSE"
        }
    else:
        token_map = {}
        for inst in instruments:
            sym = inst["tradingsymbol"]
            if sym in STOCK_SYMBOLS and inst["instrument_type"] == "EQ":
                token_map[sym] = inst["instrument_token"]

    log.info(f"Mapped {len(token_map)} symbols")
    return token_map


# ─────────────────────────────────────────────
# CORE FETCH LOGIC (runs in each thread)
# ─────────────────────────────────────────────

def date_chunks(start: datetime.date, end: datetime.date, chunk_days: int):
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + datetime.timedelta(days=chunk_days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + datetime.timedelta(days=1)


def fetch_ohlcv(token: int, from_date: datetime.date, to_date: datetime.date) -> pd.DataFrame:
    """Fetches OHLCV from Kite with shared rate limiting."""
    _rate_limiter.wait()
    kite = get_kite()
    candles = kite.historical_data(
        instrument_token=token,
        from_date=from_date,
        to_date=to_date,
        interval=INTERVAL,
        continuous=False,
        oi=False,
    )
    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles)
    df.rename(columns={"date": "timestamp"}, inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.date
    return df[["timestamp", "open", "high", "low", "close", "volume"]]


def backfill_symbol(symbol: str, token: int, output_dir: str) -> str:
    """
    Fetches and saves OHLCV for one symbol.
    Returns a status string for logging.
    Designed to run inside a thread.
    """
    out_path = Path(output_dir) / f"{symbol}.parquet"
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=YEARS_BACK * 365)

    # Resume logic
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        last_date = pd.to_datetime(existing["timestamp"]).max().date()
        if last_date >= end_date:
            return f"{symbol}: already up to date"
        start_date = last_date + datetime.timedelta(days=1)
        log.info(f"  {symbol}: resuming from {start_date}")
    else:
        existing = pd.DataFrame()
        log.info(f"  {symbol}: fresh fetch from {start_date}")

    frames = []
    for chunk_from, chunk_to in date_chunks(start_date, end_date, CHUNK_DAYS):
        retries = 3
        for attempt in range(retries):
            try:
                chunk_df = fetch_ohlcv(token, chunk_from, chunk_to)
                if not chunk_df.empty:
                    frames.append(chunk_df)
                break   # success — move to next chunk
            except Exception as e:
                err_str = str(e).lower()
                if "too many requests" in err_str or "rate" in err_str:
                    wait = ERROR_BACKOFF * (attempt + 1)
                    log.warning(f"  {symbol}: rate limited, waiting {wait}s (attempt {attempt+1}/{retries})")
                    time.sleep(wait)
                else:
                    log.error(f"  {symbol} {chunk_from}→{chunk_to}: {e}")
                    break

    if not frames:
        return f"{symbol}: no new data"

    new_data = pd.concat(frames, ignore_index=True)
    combined = pd.concat([existing, new_data], ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"])
    combined.drop_duplicates(subset=["timestamp"], inplace=True)
    combined.sort_values("timestamp", inplace=True)
    combined.reset_index(drop=True, inplace=True)
    combined.to_parquet(out_path, index=False)

    return f"{symbol}: saved {len(combined)} rows"


# ─────────────────────────────────────────────
# PROGRESS TRACKING
# ─────────────────────────────────────────────

class Progress:
    """Thread-safe progress counter."""
    def __init__(self, total: int):
        self.total    = total
        self.done     = 0
        self.failed   = 0
        self._lock    = threading.Lock()
        self._start   = time.monotonic()

    def update(self, success: bool = True):
        with self._lock:
            if success:
                self.done += 1
            else:
                self.failed += 1
            elapsed  = time.monotonic() - self._start
            per_sym  = elapsed / (self.done + self.failed)
            remaining = (self.total - self.done - self.failed) * per_sym
            log.info(
                f"Progress: {self.done + self.failed}/{self.total} "
                f"({self.done} ok, {self.failed} failed) | "
                f"ETA: {datetime.timedelta(seconds=int(remaining))}"
            )



def backfill_indices(kite: KiteConnect, output_dir: str) -> None:
    """
    Fetches 10 years of daily OHLCV for all indices in INDICES dict.
    Saves one Parquet file per index e.g. NIFTY_50.parquet
    India VIX has no volume — volume column will be 0, that's expected.
    """
    os.makedirs(output_dir, exist_ok=True)
    total = len(INDICES)

    log.info(f"\nStarting index backfill for {total} indices...")

    for i, (name, token) in enumerate(INDICES.items(), 1):
        log.info(f"[{i}/{total}] {name} (token: {token})")
        backfill_symbol(kite, name, token, output_dir)
        # backfill_symbol already handles resume, dedup, and rate limiting


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tok_map = build_instrument_map(mode="all")

    # Filter out already up-to-date symbols
    already_done = {
        p.stem for p in Path(OUTPUT_DIR).glob("*.parquet")
        if pd.read_parquet(p)["timestamp"].max().date() >= datetime.date.today()
    }
    pending = {sym: tok for sym, tok in tok_map.items() if sym not in already_done}

    log.info(f"Already up to date : {len(already_done)} symbols")
    log.info(f"Pending fetch      : {len(pending)} symbols")
    log.info(f"Workers            : {MAX_WORKERS} threads")
    log.info(f"Rate limit         : 3 req/sec shared across all threads\n")

    if not pending:
        log.info("Nothing to do.")
        return

    progress = Progress(total=len(pending))

    # backfill_indices(kite, output_dir="./data_kite/indices")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="kite") as executor:
        futures = {
            executor.submit(backfill_symbol, sym, tok, OUTPUT_DIR): sym
            for sym, tok in pending.items()
        }

        for future in as_completed(futures):
            sym = futures[future]
            try:
                result = future.result()
                log.info(f"  ✅ {result}")
                progress.update(success=True)
            except Exception as e:
                log.error(f"  ❌ {sym}: unhandled error — {e}")
                progress.update(success=False)

    log.info("\n✅ Backfill complete.")

    # Sanity check
    sample_path = Path(OUTPUT_DIR) / "RELIANCE.parquet"
    if sample_path.exists():
        df = pd.read_parquet(sample_path)
        log.info(f"\nSample — RELIANCE: {len(df)} rows, {df['timestamp'].min()} → {df['timestamp'].max()}")
        print(df.head())


if __name__ == "__main__":
    main()