"""
bhavcopy.py  —  NSE F&O Bhavcopy downloader (updated for 2024-2026 URL changes)

NSE has changed bhavcopy URLs multiple times:
  Era 1: pre-Jul 2024  → archives.nseindia.com/content/historical/DERIVATIVES/...
  Era 2: Jul 2024+     → nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_...csv.zip  (UDiFF)

This script tries both URLs in order and falls back gracefully.
"""

import io
import os
import time
import zipfile
import logging
import datetime
import requests
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)

OUTPUT_DIR = "./database/raw_data/fo_bhavcopy"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}

# Column mapping: old format → standard names
OLD_COLS = {
    "INSTRUMENT": "instrument", "SYMBOL": "symbol", "EXPIRY_DT": "expiry",
    "STRIKE_PR":  "strike",     "OPTION_TYP": "option_type",
    "OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close",
    "SETTLE_PR": "settle_price", "CONTRACTS": "contracts",
    "VAL_INLAKH": "value_lakh",  "OPEN_INT": "oi", "CHG_IN_OI": "oi_change",
    "TIMESTAMP": "date",
}

# UDiFF (new format Jul 2024+) column mapping
NEW_COLS = {
    "FinInstrmTp": "instrument", "TckrSymb": "symbol", "XpryDt": "expiry",
    "StrkPric": "strike",        "OptnTp": "option_type",
    "OpnPric": "open", "HghPric": "high", "LwPric": "low", "ClsPric": "close",
    "SttlmPric": "settle_price", "TtlTradgVol": "contracts",
    "TtlTrfVal": "value_lakh",   "OpnIntrst": "oi", "ChngInOpnIntrst": "oi_change",
    "TradDt": "date",
}

# CUTOVER DATE — old format works up to Jul 5 2024, new UDiFF from Jul 8 2024
UDIFF_CUTOVER = datetime.date(2024, 7, 8)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        # Step 1: hit homepage to get initial cookies
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(2)
        # Step 2: hit the derivatives reports page — simulates actual user navigation
        session.headers.update({"Referer": "https://www.nseindia.com/"})
        session.get("https://www.nseindia.com/all-reports-derivatives", timeout=15)
        time.sleep(1)
        # Step 3: warm up the archives subdomain
        session.headers.update({"Referer": "https://www.nseindia.com/all-reports-derivatives"})
        session.get("https://nsearchives.nseindia.com", timeout=15)
        time.sleep(0.5)
    except Exception as e:
        log.warning(f"Session warm-up failed: {e}")
    return session


def try_download(session: requests.Session, url: str) -> bytes | None:
    """Attempts to download a URL, returns raw bytes or None on failure."""
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content
    except Exception:
        pass
    return None


def parse_zip_csv(content: bytes, new_format: bool) -> pd.DataFrame:
    OPTION_TYPES = {"OPTIDX", "OPTSTK", "IO", "SO", "IDO", "STO"}   # IDO=index option, STO=stock option
    FUTURE_TYPES = {"FUTIDX", "FUTSTK", "IF", "SF", "IDF", "STF"}   # IDF=index future, STF=stock future

    z = zipfile.ZipFile(io.BytesIO(content))
    csv_names = [n for n in z.namelist() if n.endswith(".csv") and "readme" not in n.lower()]
    df = pd.read_csv(z.open(csv_names[0]))
    df.columns = [c.strip() for c in df.columns]

    # ── DEBUG: print raw columns and first instrument type values ──
    # log.info(f"  Raw columns: {list(df.columns[:10])}")
    # log.info(f"  First col unique values: {df.iloc[:, 0].unique()[:10]}")
    # ──────────────────────────────────────────────────────────────

    col_map = NEW_COLS if new_format else OLD_COLS
    df = df.rename(columns=col_map)

    keep = [c for c in col_map.values() if c in df.columns]
    df = df[keep].copy()

    if "instrument" in df.columns:
        log.info(f"  Instrument values after rename: {df['instrument'].unique()[:10]}")  # ← DEBUG
        df = df[df["instrument"].isin(OPTION_TYPES | FUTURE_TYPES)].copy()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce").dt.date

    # log.info(f"  Rows after filter: {len(df)}")  # ← DEBUG
    return df

# CUTOVER DATE — old format works up to Jul 5 2024, new UDiFF from Jul 8 2024
UDIFF_CUTOVER = datetime.date(2024, 7, 8)

def fetch_fo_bhavcopy(date: datetime.date, session: requests.Session) -> pd.DataFrame | None:
    dd   = date.strftime("%d")
    mm   = date.strftime("%m")
    mmm  = date.strftime("%b").upper()
    yyyy = date.strftime("%Y")

    if date >= UDIFF_CUTOVER:
        urls = [
            (f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyy}{mm}{dd}_F_0000.csv.zip", True),
        ]
    else:
        urls = [
            (f"https://archives.nseindia.com/content/historical/DERIVATIVES/{yyyy}/{mmm}/fo{dd}{mmm}{yyyy}bhav.csv.zip", False),
        ]

    for url, new_format in urls:
        # ── TEMPORARY DEBUG — remove after fixing ──
        r = session.get(url, timeout=15)
        # log.info(f"  URL: {url}")
        # log.info(f"  Status: {r.status_code}  Size: {len(r.content)}  Content-Type: {r.headers.get('Content-Type')}")
        # log.info(f"  First 200 bytes: {r.content[:200]}")
        # ───────────────────────────────────────────
        
        content = try_download(session, url)
        if content:
            try:
                df = parse_zip_csv(content, new_format)
                if not df.empty:
                    return df
            except Exception as e:
                log.info(f"  Parse error: {e}")

    return None






def bulk_download(
    start: datetime.date,
    end: datetime.date,
    out_dir: str = OUTPUT_DIR,
    instruments: list[str] = None,
):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    session = get_session()

    cursor = start
    done = skipped = failed = 0
    requests_since_refresh = 0          # ← add this
    SESSION_REFRESH_EVERY = 50          # ← refresh session every 50 downloads

    while cursor <= end:
        if cursor.weekday() >= 5:
            cursor += datetime.timedelta(days=1)
            continue

        out_path = Path(out_dir) / f"{cursor.isoformat()}.parquet"

        if out_path.exists():
            log.info(f"  {cursor}: already exists, skipping")
            skipped += 1
            cursor += datetime.timedelta(days=1)
            continue

        # ── Refresh session periodically ──────────────────────────
        if requests_since_refresh >= SESSION_REFRESH_EVERY:
            log.info("  Refreshing NSE session cookies...")
            session = get_session()
            requests_since_refresh = 0
        # ──────────────────────────────────────────────────────────

        log.info(f"  {cursor}: downloading...")
        df = fetch_fo_bhavcopy(cursor, session)
        requests_since_refresh += 1

        if df is not None and not df.empty:
            if instruments:
                df = df[df["symbol"].isin(instruments)]
            df.to_parquet(out_path, index=False)
            log.info(f"    → {len(df)} rows saved")
            done += 1
        else:
            log.info(f"    → no data (holiday or URL unavailable)")
            failed += 1

        time.sleep(0.4)
        cursor += datetime.timedelta(days=1)

    log.info(f"\n✅ Done — downloaded: {done}, skipped: {skipped}, no data: {failed}")





def load_all(out_dir: str = OUTPUT_DIR, symbol: str = None) -> pd.DataFrame:
    """Loads all saved parquet files into one DataFrame, optionally filtered by symbol."""
    files = sorted(Path(out_dir).glob("*.parquet"))
    if not files:
        log.warning("No parquet files found")
        return pd.DataFrame()

    dfs = [pd.read_parquet(f) for f in files]
    df  = pd.concat(dfs, ignore_index=True)

    if symbol:
        df = df[df["symbol"] == symbol]

    df = df.sort_values(["symbol", "expiry", "strike", "option_type", "date"])
    return df


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── Sanity check before bulk run ──
    log.info("Testing connection to NSE archives...")
    test_session = get_session()
    test_url = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv.zip"
    test_r = test_session.get(test_url, timeout=15)
    if test_r.status_code == 200 and len(test_r.content) > 1000:
        log.info(f"✅ Connection OK — got {len(test_r.content)/1024:.0f} KB")
    else:
        log.error(f"❌ Connection failed — status {test_r.status_code}, size {len(test_r.content)}")
        log.error("Check your internet connection or try again in a few minutes")
        exit(1)

    # Full 10-year backfill — just NIFTY + BANKNIFTY to keep it manageable
    # Remove the `instruments` filter to get ALL F&O stocks (much larger)
    bulk_download(
        start=datetime.date(2024, 7, 6),
        end=datetime.date.today(),
        out_dir=OUTPUT_DIR,
        instruments=["NIFTY", "BANKNIFTY", "FINNIFTY"],
    )

    # Quick check
    df = load_all(OUTPUT_DIR, symbol="NIFTY")
    print(f"\nNIFTY options rows: {len(df)}")
    print(df[["date", "expiry", "strike", "option_type", "open", "high", "low", "close", "oi"]].head(10))