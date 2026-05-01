import pandas as pd
import numpy as np
import mplfinance as mpf

# =========================
# 📈 MOVING AVERAGES
# =========================

def add_sma(df, period=20):
    df[f"sma_{period}"] = df["close"].rolling(period).mean()
    return df


def add_ema(df, period=20):
    df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
    return df


def add_vwap(df):
    price = (df["high"] + df["low"] + df["close"]) / 3
    vol_price = price * df["volume"]
    df["vwap"] = vol_price.cumsum() / df["volume"].cumsum()
    return df


# =========================
# ⚡ MOMENTUM
# =========================

def add_rsi(df, period=14):
    delta = df["close"].diff()

    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    return df


def add_macd(df):
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def add_roc(df, period=12):
    df[f"roc_{period}"] = df["close"].pct_change(periods=period)
    return df


def add_stochastic(df, k_period=14, d_period=3):
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()

    df["stoch_k"] = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-9)
    df["stoch_d"] = df["stoch_k"].rolling(d_period).mean()

    return df


# =========================
# 📊 VOLUME
# =========================

def add_obv(df):
    obv = [0]

    for i in range(1, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i - 1]:
            obv.append(obv[-1] + df["volume"].iloc[i])
        elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
            obv.append(obv[-1] - df["volume"].iloc[i])
        else:
            obv.append(obv[-1])

    df["obv"] = obv
    return df


def add_mfi(df, period=14):
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    money_flow = typical_price * df["volume"]

    positive_flow = []
    negative_flow = []

    for i in range(1, len(df)):
        if typical_price.iloc[i] > typical_price.iloc[i - 1]:
            positive_flow.append(money_flow.iloc[i])
            negative_flow.append(0)
        else:
            positive_flow.append(0)
            negative_flow.append(money_flow.iloc[i])

    pos_mf = pd.Series(positive_flow).rolling(period).sum()
    neg_mf = pd.Series(negative_flow).rolling(period).sum()

    mfi = 100 - (100 / (1 + (pos_mf / (neg_mf + 1e-9))))
    df["mfi"] = mfi

    return df


def add_accumulation_distribution(df):
    clv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (
        df["high"] - df["low"] + 1e-9
    )
    df["ad_line"] = (clv * df["volume"]).cumsum()
    return df


# =========================
# 📉 VOLATILITY
# =========================

def add_atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())

    tr = np.maximum(high_low, np.maximum(high_close, low_close))
    df["atr"] = tr.rolling(period).mean()

    return df


def add_bollinger_bands(df, period=20, std_dev=2):
    sma = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()

    df["bb_middle"] = sma
    df["bb_upper"] = sma + std_dev * std
    df["bb_lower"] = sma - std_dev * std

    return df


# =========================
# 🧠 STRUCTURE
# =========================

def add_pivot_points(df):
    pivot = (df["high"] + df["low"] + df["close"]) / 3

    df["pivot"] = pivot
    df["r1"] = 2 * pivot - df["low"]
    df["s1"] = 2 * pivot - df["high"]

    return df


def add_fibonacci_levels(df, window=50):
    recent_high = df["high"].rolling(window).max()
    recent_low = df["low"].rolling(window).min()

    diff = recent_high - recent_low

    df["fib_0.236"] = recent_high - 0.236 * diff
    df["fib_0.382"] = recent_high - 0.382 * diff
    df["fib_0.5"] = recent_high - 0.5 * diff
    df["fib_0.618"] = recent_high - 0.618 * diff

    return df


# =========================
# 🚀 MASTER FUNCTION
# =========================

def add_indicators(df, indicators=None):
    df = df.copy()

    # Default = all
    if indicators is None:
        indicators = [
            "sma", "ema", "vwap",
            "rsi", "macd", "roc", "stochastic",
            "obv", "mfi", "ad",
            "atr", "bollinger",
            "pivot", "fibonacci"
        ]

    if "sma" in indicators:
        df = add_sma(df)

    if "ema" in indicators:
        df = add_ema(df)

    if "vwap" in indicators:
        df = add_vwap(df)

    if "rsi" in indicators:
        df = add_rsi(df)

    if "macd" in indicators:
        df = add_macd(df)

    if "roc" in indicators:
        df = add_roc(df)

    if "stochastic" in indicators:
        df = add_stochastic(df)

    if "obv" in indicators:
        df = add_obv(df)

    if "mfi" in indicators:
        df = add_mfi(df)

    if "ad" in indicators:
        df = add_accumulation_distribution(df)

    if "atr" in indicators:
        df = add_atr(df)

    if "bollinger" in indicators:
        df = add_bollinger_bands(df)

    if "pivot" in indicators:
        df = add_pivot_points(df)

    if "fibonacci" in indicators:
        df = add_fibonacci_levels(df)

    return df












def plot_with_indicators(df, indicators=None):
    df_plot = df.copy()

    # Rename for mplfinance
    df_plot = df_plot.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })

    # Ensure datetime index
    df_plot.index = pd.to_datetime(df_plot.index)

    # Default: no indicators
    if indicators is None:
        indicators = []

    apds = []
    panel_id = 1  # 0 = main candle panel

    # =========================
    # Categorize indicators
    # =========================

    overlay_indicators = []
    separate_indicators = []

    for col in indicators:
        if col not in df_plot.columns:
            continue

        # Heuristic: price-like indicators → overlay
        if any(key in col.lower() for key in [
            "ema", "sma", "vwap", "bb_", "kc_", "donchian"
        ]):
            overlay_indicators.append(col)
        else:
            separate_indicators.append(col)

    # =========================
    # Overlay indicators
    # =========================
    for col in overlay_indicators:
        apds.append(
            mpf.make_addplot(
                df_plot[col],
                panel=0
            )
        )

    # =========================
    # Separate panel indicators
    # =========================
    for col in separate_indicators:
        series = df_plot[col]

        # Skip if empty / all NaN
        if series.isna().all():
            continue

        apds.append(
            mpf.make_addplot(
                series,
                panel=panel_id
            )
        )
        panel_id += 1

    # =========================
    # Plot
    # =========================
    fig, axlist = mpf.plot(
        df_plot,
        type="candle",
        style="charles",
        addplot=apds if len(apds) > 0 else None,
        figsize=(14, 8),
        datetime_format="%Y-%m-%d",
        xrotation=45,
        returnfig=True
    )

    return fig















