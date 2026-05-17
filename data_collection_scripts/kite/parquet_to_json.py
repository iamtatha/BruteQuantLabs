"""
parquet_to_json.py

Converts Kite OHLCV Parquet files → JSON in the format:
{
    "2026-04-29": {
        "Open_RELIANCE.NS": 1234.5,
        "High_RELIANCE.NS": 1250.0,
        "Low_RELIANCE.NS":  1220.0,
        "Close_RELIANCE.NS": 1240.0,
        "Volume_RELIANCE.NS": 3812000
    },
    ...
}

Usage:
    # Combined JSON (all stocks in one file):
    python parquet_to_json.py --mode combined --input ./data/historical --output ./data/nifty50.json

    # One JSON per stock:
    python parquet_to_json.py --mode split --input ./data/historical --output ./data/json

Flags:
    --suffix     Suffix appended to symbol in key names. Default: .NS  (set to "" for none)
    --mode       "combined" (default) or "split"
    --input      Directory containing .parquet files
    --output     Output file (combined) or output directory (split)
    --date-from  Optional start date filter: YYYY-MM-DD
    --date-to    Optional end date filter:   YYYY-MM-DD
"""

import os
import json
import argparse
import logging
import pandas as pd
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def load_parquet(path: Path, date_from: str = None, date_to: str = None) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    if date_from:
        df = df[df["timestamp"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["timestamp"] <= pd.Timestamp(date_to)]

    return df


def df_to_dated_dict(df: pd.DataFrame, symbol: str, suffix: str) -> dict:
    """
    Converts a single stock DataFrame to:
    {
        "2026-04-29": {
            "Open_RELIANCE.NS": ...,
            "High_RELIANCE.NS": ...,
            ...
        },
        ...
    }
    """
    key = f"{symbol}{suffix}"
    result = {}

    for _, row in df.iterrows():
        date_str = row["timestamp"].strftime("%Y-%m-%d")
        result[date_str] = {
            f"Open_{key}":   row["open"],
            f"High_{key}":   row["high"],
            f"Low_{key}":    row["low"],
            f"Close_{key}":  row["close"],
            f"Volume_{key}": int(row["volume"]),
        }

    return result


def build_combined(
    parquet_dir: Path,
    suffix: str,
    date_from: str,
    date_to: str,
) -> dict:
    """
    Merges all stocks into one dict keyed by date.
    Each date entry contains OHLCV columns for ALL stocks.
    """
    combined = {}
    parquet_files = sorted(parquet_dir.glob("*.parquet"))

    if not parquet_files:
        log.error(f"No .parquet files found in {parquet_dir}")
        return {}

    for pf in parquet_files:
        symbol = pf.stem  # e.g. "RELIANCE" from "RELIANCE.parquet"
        log.info(f"  Processing {symbol}...")

        df = load_parquet(pf, date_from, date_to)
        dated = df_to_dated_dict(df, symbol, suffix)

        for date_str, cols in dated.items():
            if date_str not in combined:
                combined[date_str] = {}
            combined[date_str].update(cols)

    # Sort by date
    combined = dict(sorted(combined.items()))
    return combined


def build_split(
    parquet_dir: Path,
    suffix: str,
    date_from: str,
    date_to: str,
    output_dir: Path,
):
    """Writes one JSON file per stock."""
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_files = sorted(parquet_dir.glob("*.parquet"))

    if not parquet_files:
        log.error(f"No .parquet files found in {parquet_dir}")
        return

    for pf in parquet_files:
        symbol = pf.stem
        log.info(f"  Processing {symbol}...")

        df = load_parquet(pf, date_from, date_to)
        dated = df_to_dated_dict(df, symbol, suffix)
        dated = dict(sorted(dated.items()))

        out_path = output_dir / f"{symbol}.json"
        with open(out_path, "w") as f:
            json.dump(dated, f, indent=4)

        log.info(f"    → {out_path}  ({len(dated)} dates)")


def main():
    parser = argparse.ArgumentParser(description="Convert Kite Parquet files to JSON")
    parser.add_argument("--input",     default="./data_kite/historical",  help="Directory with .parquet files")
    parser.add_argument("--output",    default="./database/historical_data_kite", help="Output file (combined) or dir (split)")
    parser.add_argument("--mode",      default="split", choices=["combined", "split"])
    parser.add_argument("--suffix",    default=".NS", help='Symbol suffix in key names (default: .NS, use "" for none)')
    parser.add_argument("--date-from", default=None,  help="Start date filter YYYY-MM-DD")
    parser.add_argument("--date-to",   default=None,  help="End date filter YYYY-MM-DD")
    args = parser.parse_args()

    parquet_dir = Path(args.input)
    if not parquet_dir.exists():
        log.error(f"Input directory not found: {parquet_dir}")
        return

    log.info(f"Mode     : {args.mode}")
    log.info(f"Input    : {parquet_dir}")
    log.info(f"Output   : {args.output}")
    log.info(f"Suffix   : '{args.suffix}'")
    if args.date_from: log.info(f"From     : {args.date_from}")
    if args.date_to:   log.info(f"To       : {args.date_to}")
    log.info("")

    if args.mode == "combined":
        data = build_combined(parquet_dir, args.suffix, args.date_from, args.date_to)
        if data:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(data, f, indent=4)
            log.info(f"\n✅ Done. {len(data)} dates → {out_path}")
            log.info(f"   File size: {out_path.stat().st_size / 1024 / 1024:.1f} MB")

    elif args.mode == "split":
        build_split(parquet_dir, args.suffix, args.date_from, args.date_to, Path(args.output))
        log.info(f"\n✅ Done. Files written to {args.output}")


if __name__ == "__main__":
    main()