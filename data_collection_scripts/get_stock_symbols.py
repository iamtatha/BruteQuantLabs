import pandas as pd
import requests
import sqlite3

# Step 1: Download all NSE stocks
url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)

print(r.content)

# Step 2: Parse CSV
with open("database/nse_equity_list.csv", "wb") as f:
    f.write(r.content)

df = pd.read_csv("database/nse_equity_list.csv")
df = df[["SYMBOL", "NAME OF COMPANY"]]

print("Total NSE stocks:", len(df))
print(df.head())

# Step 3: Format tickers for Yahoo Finance (add .NS suffix)
df["YF_TICKER"] = df["SYMBOL"].apply(lambda x: x + ".NS")

print("\nSample Yahoo Finance Tickers:")
print(df["YF_TICKER"].head())



conn = sqlite3.connect("database/bql_stock_summary.db")
df.to_sql("stock_list", conn, if_exists="append", index=False)
conn.close()






# Step 1: Download all NSE stocks
url = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)

print(r.content)

# Step 2: Parse CSV
with open("database/static_data/nifty_500.csv", "wb") as f:
    f.write(r.content)

df = pd.read_csv("database/static_data/nifty_500.csv")
df = df[["Symbol", "Company Name", "Industry"]]

print("Total NSE stocks:", len(df))
print(df.head())

# Step 3: Format tickers for Yahoo Finance (add .NS suffix)
df["YF_TICKER"] = df["Symbol"].apply(lambda x: x + ".NS")

print("\nSample Yahoo Finance Tickers:")
print(df["YF_TICKER"].head())

with open("database/static_data/nifty_500.csv", "wb") as f:
    f.write(df.to_csv(index=False).encode())
f.close()


conn = sqlite3.connect("database/bql_stock_summary.db")
df.to_sql("nifty_500", conn, if_exists="append", index=False)
conn.close()












# Step 1: Download all NSE stocks
url = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)

print(r.content)

# Step 2: Parse CSV
with open("database/static_data/nifty_50.csv", "wb") as f:
    f.write(r.content)

df = pd.read_csv("database/static_data/nifty_50.csv")
df = df[["Symbol", "Company Name", "Industry"]]

print("Total NSE stocks:", len(df))
print(df.head())

# Step 3: Format tickers for Yahoo Finance (add .NS suffix)
df["YF_TICKER"] = df["Symbol"].apply(lambda x: x + ".NS")

print("\nSample Yahoo Finance Tickers:")
print(df["YF_TICKER"].head())

with open("database/static_data/nifty_50.csv", "wb") as f:
    f.write(df.to_csv(index=False).encode())
f.close()


conn = sqlite3.connect("database/bql_stock_summary.db")
df.to_sql("nifty_50", conn, if_exists="append", index=False)
conn.close()

