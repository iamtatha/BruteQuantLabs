import pandas as pd

prices_dir = "database/historical_data_yf"
stock_code = "TCS"


def load_data(stock):
    file_path = f"{prices_dir}/{stock}.NS_yf.json"
    df = pd.read_json(file_path).T
    
    dates = pd.to_datetime(df.index.tolist()).tolist()
    
    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock}.NS", '').lower() for c in cols]
    df.columns = cols
    return df, dates, cols

df, dates, cols = load_data(stock_code)

from utils.candles import detect_candles

last_100 = df[dates[-100]:]

candle = detect_candles(last_100)
candle.head()



from utils.candles import plot_with_annotations


plot_with_annotations(candle)



