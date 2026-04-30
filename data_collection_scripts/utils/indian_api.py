import requests
import json
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime
import sqlite3

load_dotenv()

# Read values
api_key = os.getenv("X-Api-Key")

stock_name = "TCS"
period = "3yr"
filter = "price"


endpoint_maps = {
    "historical_data": ["stock_name", "period", "filter"],
    "trending": [],
    "statement": ["stock_name", "stats"],
    "BSE_most_active": [],
    "NSE_most_active": [],
}

param_options = {
    "period": ["1mo", "6mo", "1yr", "3yr", "5yr", "10yr", "max"],
    "filter": ["default", "price", "pe", "sm", "evebitda", "ptb", "mcs"],
    "stats": ["yoy_results", "quarter_results", "balancesheet"],
}

headers = {
    "X-Api-Key": api_key
}


def get_data(endpoint, stock_name, period="1yr", filter="default", stats="yoy_results"):
    param_extra = {"period": period, "filter": filter, "stats": stats}
    url = f"https://stock.indianapi.in/{endpoint}"

    params = {}
    for key in endpoint_maps[endpoint]:
        if key == "stock_name":
            params[key] = stock_name
        elif key in param_options:
            params[key] = param_extra[key]

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
        
    else:
        print(f"Error: {response.status_code} - {response.text}")


def parse_into_df(json_data):
    dfs = []
    for dataset in json_data["datasets"]:
        metric = dataset["metric"]
        values = dataset["values"]

        rows = []
        for v in values:
            row = {"date": v[0], metric: v[1]}
            
            # Handle extra fields (like delivery in Volume)
            if len(v) > 2 and isinstance(v[2], dict):
                for k, val in v[2].items():
                    row[f"{metric}_{k}"] = val
            
            rows.append(row)

        df = pd.DataFrame(rows)
        dfs.append(df)

    # Merge all datasets on date
    from functools import reduce
    final_df = reduce(lambda left, right: pd.merge(left, right, on="date", how="outer"), dfs)

    # Convert types
    final_df["date"] = pd.to_datetime(final_df["date"])
    for col in final_df.columns:
        if col != "date":
            final_df[col] = pd.to_numeric(final_df[col], errors="coerce")

    # Sort
    final_df = final_df.sort_values("date").reset_index(drop=True)

    return final_df




def get_or_load_data(endpoint, stock_name, period="3yr", filter="default", stats="yoy_results"):
    # File path for cached data
    os.makedirs(f"database/{endpoint}", exist_ok=True)
    file_path = f"database/{endpoint}/{stock_name}_{period}_{filter}_{stats}_{str(datetime.now().strftime("%d-%m-%Y"))}.json"

    # If file exists, load it
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            json_data = json.load(f)
        print(f"Loaded from cache: {file_path}")
    else:
        # Otherwise fetch from API
        json_data = get_data(endpoint, stock_name, period=period, filter=filter, stats=stats)

        # Save to file
        with open(file_path, "w") as f:
            json.dump(json_data, f, indent=2)
        
        _df = parse_into_df(json_data)
        conn = sqlite3.connect("database/bql_stock_prices.db")
        _df.to_sql(f"{stock_name}", conn, if_exists="append", index=False)
        conn.close()


        print(f"Saved new data to: {file_path}")

    return json_data

