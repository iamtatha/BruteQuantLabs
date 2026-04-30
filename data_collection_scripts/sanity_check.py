import os
import json
import pandas as pd

def sanity_check_json_folder(folder_path: str):
    """
    For each JSON file:
    - load into DataFrame
    - normalize schema
    - check:
        high >= low
        volume >= 0
    - print violations
    """

    def normalize_df(df):
        # transpose if needed (json saved as index→rows)
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df = df.T
            except:
                pass

        # normalize index
        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df[~df.index.isna()]

        # normalize columns (lowercase, remove ticker suffix)
        new_cols = {}
        for col in df.columns:
            c = str(col).lower()

            if "high" in c:
                new_cols[col] = "high"
            elif "low" in c:
                new_cols[col] = "low"
            elif "open" in c:
                new_cols[col] = "open"
            elif "close" in c:
                new_cols[col] = "close"
            elif "volume" in c:
                new_cols[col] = "volume"

        df = df.rename(columns=new_cols)

        # keep only relevant columns
        keep_cols = [c for c in ["open","high","low","close","volume"] if c in df.columns]
        return df[keep_cols]

    # ----------------------------
    # Iterate files
    # ----------------------------
    failed_stocks = []

    for file in os.listdir(folder_path):
        if not file.endswith(".json"):
            continue

        file_path = os.path.join(folder_path, file)

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            df = pd.DataFrame(data)
            df = normalize_df(df)

            if df.empty:
                print(f"[SKIP] {file} → empty or invalid")
                continue

            # ----------------------------
            # Checks
            # ----------------------------
            if "high" in df.columns and "low" in df.columns:
                bad_hl = df[df["high"] < df["low"]]
                if not bad_hl.empty:
                    print(f"[FAIL] {file} → high < low")
                    print(bad_hl.head())
                    failed_stocks.append(file)

            if "volume" in df.columns:
                bad_vol = df[df["volume"] < 0]
                if not bad_vol.empty:
                    print(f"[FAIL] {file} → negative volume")
                    print(bad_vol.head())
                    failed_stocks.append(file)

        except Exception as e:
            print(f"[ERROR] {file} → {e}")

    return failed_stocks





folder_path = "database/historical_data_yf"
failed_files = sanity_check_json_folder(folder_path)

print(failed_files)

