"""
options_to_sqlite.py

Loads all F&O bhavcopy Parquet files into:
  1. A clean pandas DataFrame (for in-memory use)
  2. A SQLite database (for persistent querying)

Schema (table: options):
    date          TEXT     trading date         e.g. 2024-07-08
    symbol        TEXT     underlying           e.g. NIFTY, BANKNIFTY
    expiry        TEXT     contract expiry      e.g. 2024-07-25
    strike        REAL     strike price         e.g. 24000.0
    option_type   TEXT     CE or PE             e.g. CE
    instrument    TEXT     IDO/STO/OPTIDX etc.
    open          REAL
    high          REAL
    low           REAL
    close         REAL
    settle_price  REAL
    contracts     INTEGER  lots traded
    value_lakh    REAL     traded value in lakhs
    oi            INTEGER  open interest
    oi_change     INTEGER  change in OI vs prev day

Usage:
    # Load everything into SQLite (run once, then query forever)
    python options_to_sqlite.py --input ./data/fo_bhavcopy --db ./data/options.db

    # Load only NIFTY + BANKNIFTY
    python options_to_sqlite.py --input ./data/fo_bhavcopy --db ./data/options.db --symbols NIFTY BANKNIFTY

    # Incremental update (only adds new dates not already in DB)
    python options_to_sqlite.py --input ./data/fo_bhavcopy --db ./data/options.db --incremental

    # Load into DataFrame only (no SQLite), useful for notebooks
    from options_to_sqlite import load_parquets_to_df
    df = load_parquets_to_df("./data/fo_bhavcopy", symbols=["NIFTY"])
"""

import os
import argparse
import logging
import sqlite3
import datetime
import pandas as pd
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS options (
    date          TEXT    NOT NULL,
    symbol        TEXT    NOT NULL,
    expiry        TEXT    NOT NULL,
    strike        REAL,
    option_type   TEXT,
    instrument    TEXT,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL,
    settle_price  REAL,
    contracts     INTEGER,
    value_lakh    REAL,
    oi            INTEGER,
    oi_change     INTEGER,
    PRIMARY KEY (date, symbol, expiry, strike, option_type)
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_date         ON options (date);",
    "CREATE INDEX IF NOT EXISTS idx_symbol        ON options (symbol);",
    "CREATE INDEX IF NOT EXISTS idx_symbol_date   ON options (symbol, date);",
    "CREATE INDEX IF NOT EXISTS idx_expiry        ON options (expiry);",
    "CREATE INDEX IF NOT EXISTS idx_strike        ON options (strike);",
    "CREATE INDEX IF NOT EXISTS idx_option_type   ON options (option_type);",
    # Composite index for the most common query pattern:
    # WHERE symbol=X AND expiry=Y AND date BETWEEN a AND b
    "CREATE INDEX IF NOT EXISTS idx_symbol_expiry_date ON options (symbol, expiry, date);",
]

# ── Parquet loading ────────────────────────────────────────────────────────────

EXPECTED_COLS = [
    "date", "symbol", "expiry", "strike", "option_type", "instrument",
    "open", "high", "low", "close", "settle_price",
    "contracts", "value_lakh", "oi", "oi_change",
]

DTYPES = {
    "date":         "str",
    "symbol":       "str",
    "expiry":       "str",
    "strike":       "float64",
    "option_type":  "str",
    "instrument":   "str",
    "open":         "float64",
    "high":         "float64",
    "low":          "float64",
    "close":        "float64",
    "settle_price": "float64",
    "contracts":    "Int64",    # nullable int
    "value_lakh":   "float64",
    "oi":           "Int64",
    "oi_change":    "Int64",
}


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures consistent column names, types, and filters out
    non-option rows (futures etc.) and zero-volume garbage rows.
    """
    # Rename any stray column variants
    df.columns = [c.strip() for c in df.columns]

    # Keep only columns we care about — fill missing ones with NaN
    for col in EXPECTED_COLS:
        if col not in df.columns:
            df[col] = None

    df = df[EXPECTED_COLS].copy()

    # Normalize date/expiry to ISO string YYYY-MM-DD
    for col in ["date", "expiry"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    # Normalize option_type: CE/PE only (drop futures XX/NaN)
    df = df[df["option_type"].isin(["CE", "PE"])].copy()

    # Drop rows with missing core fields
    df = df.dropna(subset=["date", "symbol", "expiry", "strike", "option_type"])

    # Drop zero-close rows (untradeable strikes — no price discovery)
    df = df[df["close"] > 0].copy()

    # Cast types
    for col, dtype in DTYPES.items():
        if col in df.columns:
            try:
                df[col] = df[col].astype(dtype)
            except Exception:
                pass

    df = df.sort_values(["date", "symbol", "expiry", "strike", "option_type"])
    df = df.reset_index(drop=True)
    return df


def load_parquets_to_df(
    input_dir: str,
    symbols: list[str] = None,
    date_from: str = None,
    date_to:   str = None,
) -> pd.DataFrame:
    """
    Loads all Parquet files from input_dir into a single DataFrame.

    Args:
        input_dir:  Directory containing dated .parquet files (e.g. 2024-07-08.parquet)
        symbols:    Optional list to filter e.g. ["NIFTY", "BANKNIFTY"]
        date_from:  Optional start date string "YYYY-MM-DD"
        date_to:    Optional end date string   "YYYY-MM-DD"

    Returns:
        Clean normalized DataFrame
    """
    files = sorted(Path(input_dir).glob("*.parquet"))
    if not files:
        log.warning(f"No parquet files found in {input_dir}")
        return pd.DataFrame()

    # Filter files by date range (filename is the date)
    if date_from:
        files = [f for f in files if f.stem >= date_from]
    if date_to:
        files = [f for f in files if f.stem <= date_to]

    log.info(f"Loading {len(files)} parquet files...")

    frames = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            if symbols:
                df = df[df["symbol"].isin(symbols)]
            if not df.empty:
                frames.append(df)
        except Exception as e:
            log.warning(f"  Skipping {f.name}: {e}")

    if not frames:
        log.warning("No data loaded")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = normalize_df(combined)

    log.info(f"Loaded {len(combined):,} rows across {combined['date'].nunique()} dates")
    if symbols:
        log.info(f"Symbols: {combined['symbol'].unique().tolist()}")

    return combined


# ── SQLite ────────────────────────────────────────────────────────────────────

def init_db(db_path: str) -> sqlite3.Connection:
    """Creates the database, table, and indexes if they don't exist."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")   # faster concurrent writes
    conn.execute("PRAGMA synchronous=NORMAL;") # safe but faster than FULL
    conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
    conn.execute(CREATE_TABLE_SQL)
    for idx_sql in CREATE_INDEXES_SQL:
        conn.execute(idx_sql)
    conn.commit()
    return conn


def get_existing_dates(conn: sqlite3.Connection) -> set[str]:
    """Returns the set of dates already loaded into the DB."""
    rows = conn.execute("SELECT DISTINCT date FROM options").fetchall()
    return {r[0] for r in rows}


def insert_df(conn: sqlite3.Connection, df: pd.DataFrame, batch_size: int = 10000):
    """
    Inserts DataFrame rows into the options table.
    Uses INSERT OR IGNORE to skip duplicates (safe for re-runs).
    """
    if df.empty:
        return 0

    # Convert nullable ints to plain Python ints for SQLite
    df = df.copy()
    for col in ["contracts", "oi", "oi_change"]:
        if col in df.columns:
            df[col] = df[col].astype(object).where(df[col].notna(), None)

    cols   = EXPECTED_COLS
    placeholders = ", ".join(["?"] * len(cols))
    sql    = f"INSERT OR IGNORE INTO options ({', '.join(cols)}) VALUES ({placeholders})"

    records = df[cols].values.tolist()
    inserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        conn.executemany(sql, batch)
        conn.commit()
        inserted += len(batch)

    return inserted


def load_to_sqlite(
    input_dir:   str,
    db_path:     str,
    symbols:     list[str] = None,
    date_from:   str = None,
    date_to:     str = None,
    incremental: bool = True,
):
    """
    Main function: loads Parquet files and writes to SQLite.

    Args:
        input_dir:   Directory with .parquet files
        db_path:     Path to SQLite file (created if not exists)
        symbols:     Filter to specific underlyings
        date_from:   Start date filter YYYY-MM-DD
        date_to:     End date filter YYYY-MM-DD
        incremental: If True, skip dates already in DB (default True)
    """
    conn = init_db(db_path)

    existing_dates = get_existing_dates(conn) if incremental else set()
    if existing_dates:
        log.info(f"DB has {len(existing_dates)} dates already — will skip those")

    files = sorted(Path(input_dir).glob("*.parquet"))
    if date_from:
        files = [f for f in files if f.stem >= date_from]
    if date_to:
        files = [f for f in files if f.stem <= date_to]
    if incremental:
        files = [f for f in files if f.stem not in existing_dates]

    if not files:
        log.info("Nothing new to load — DB is already up to date")
        conn.close()
        return

    log.info(f"Processing {len(files)} new files...")

    total_inserted = 0
    for i, f in enumerate(files, 1):
        try:
            df = pd.read_parquet(f)
            if symbols:
                df = df[df["symbol"].isin(symbols)]
            df = normalize_df(df)

            if df.empty:
                log.info(f"  [{i}/{len(files)}] {f.stem}: empty after filter")
                continue

            n = insert_df(conn, df)
            total_inserted += n
            log.info(f"  [{i}/{len(files)}] {f.stem}: +{n:,} rows")

        except Exception as e:
            log.error(f"  [{i}/{len(files)}] {f.stem}: ERROR — {e}")

    conn.close()
    log.info(f"\n✅ Done — {total_inserted:,} rows inserted into {db_path}")


# ── Query helpers (import these in your notebooks/scripts) ────────────────────

def query(db_path: str, sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run any SQL query and return a DataFrame."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def get_option_chain(db_path: str, symbol: str, expiry: str, date: str) -> pd.DataFrame:
    """
    Returns the full option chain for a symbol on a given date for one expiry.

    Example:
        chain = get_option_chain("options.db", "NIFTY", "2024-07-25", "2024-07-22")
    """
    return query(db_path, """
        SELECT strike, option_type, open, high, low, close, oi, oi_change, contracts
        FROM options
        WHERE symbol = ? AND expiry = ? AND date = ?
        ORDER BY strike, option_type
    """, (symbol, expiry, date))


def get_strike_history(
    db_path: str, symbol: str, expiry: str,
    strike: float, option_type: str
) -> pd.DataFrame:
    """
    Returns daily OHLCV + OI for a specific contract across its entire life.

    Example:
        df = get_strike_history("options.db", "NIFTY", "2024-07-25", 24000.0, "CE")
    """
    return query(db_path, """
        SELECT date, open, high, low, close, settle_price, contracts, oi, oi_change
        FROM options
        WHERE symbol = ? AND expiry = ? AND strike = ? AND option_type = ?
        ORDER BY date
    """, (symbol, expiry, strike, option_type))


def get_db_summary(db_path: str):
    """Prints a summary of what's in the database."""
    conn = sqlite3.connect(db_path)
    total   = conn.execute("SELECT COUNT(*) FROM options").fetchone()[0]
    dates   = conn.execute("SELECT COUNT(DISTINCT date) FROM options").fetchone()[0]
    symbols = conn.execute("SELECT DISTINCT symbol FROM options ORDER BY symbol").fetchall()
    min_dt  = conn.execute("SELECT MIN(date) FROM options").fetchone()[0]
    max_dt  = conn.execute("SELECT MAX(date) FROM options").fetchone()[0]
    size_mb = os.path.getsize(db_path) / 1024 / 1024
    conn.close()

    print(f"\n{'='*50}")
    print(f"  Database: {db_path}")
    print(f"  Size:     {size_mb:.1f} MB")
    print(f"  Rows:     {total:,}")
    print(f"  Dates:    {dates} ({min_dt} → {max_dt})")
    print(f"  Symbols:  {[r[0] for r in symbols]}")
    print(f"{'='*50}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load F&O bhavcopy parquets into SQLite")
    parser.add_argument("--input",       default="./database/raw_data/fo_bhavcopy", help="Parquet directory")
    parser.add_argument("--db",          default="./database/options.db",  help="SQLite database path")
    parser.add_argument("--symbols",     nargs="+", default=None,      help="Filter symbols e.g. NIFTY BANKNIFTY")
    parser.add_argument("--date-from",   default=None,                 help="Start date YYYY-MM-DD")
    parser.add_argument("--date-to",     default=None,                 help="End date YYYY-MM-DD")
    parser.add_argument("--incremental", action="store_true", default=True,
                        help="Skip dates already in DB (default: True)")
    parser.add_argument("--full",        action="store_true",
                        help="Full reload — ignore existing data in DB")
    parser.add_argument("--summary",     action="store_true",
                        help="Print DB summary and exit")
    args = parser.parse_args()

    if args.summary:
        get_db_summary(args.db)
        exit(0)

    load_to_sqlite(
        input_dir   = args.input,
        db_path     = args.db,
        symbols     = args.symbols,
        date_from   = args.date_from,
        date_to     = args.date_to,
        incremental = not args.full,
    )

    get_db_summary(args.db)