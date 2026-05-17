import pandas as pd
import numpy as np
import mplfinance as mpf

# =========================
# 📈 MOVING AVERAGES
# =========================

def add_sma(df, period=20, col="close"):
    if col == "volume":
        df[f"sma_{col}"] = df[col].rolling(period).mean()
        return df
    df[f"sma_{period}"] = df[col].rolling(period).mean()
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

    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    
    df["rsi"] = rsi.values  # Use .values to avoid index mismatch
    
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
        df = add_sma(df, period=50)
        df = add_sma(df, period=200)
        df = add_sma(df, col="volume")

    if "ema" in indicators:
        df = add_ema(df)
        df = add_ema(df, period=7)
        df = add_ema(df, period=33)

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
        indicators = [
            "sma_20", "ema_20", "vwap",
            "rsi", "macd", "macd_signal", "macd_hist", 
            "roc_12", "stoch_k", "stoch_d",
            "obv", "mfi", "ad_line",
            "atr", 
            "bb_middle", "bb_upper", "bb_lower",
            "pivot", "r1", "s1", 
            "fib_0.236", "fib_0.382", "fib_0.5", "fib_0.618"
        ]

    apds = []

    # Color palette for indicators
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    color_idx = 0

    # Calculate average price for normalization
    price_avg = df_plot['Close'].mean()

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
            "ema", "sma", "bb_", "kc_", "donchian"
        ]):
            overlay_indicators.append(col)
        else:
            separate_indicators.append(col)

    # =========================
    # Overlay indicators (price-like, no scaling needed)
    # =========================
    for col in overlay_indicators:
        series = df_plot[col].dropna()
        if len(series) > 0:
            min_val = series.min()
            max_val = series.max()
            label = f"{col} [{min_val:.2f} - {max_val:.2f}]"
        else:
            label = col
            
        apds.append(
            mpf.make_addplot(
                df_plot[col],
                panel=0,  # Same panel as candlesticks
                label=label,
                color=colors[color_idx % len(colors)],
                alpha=0.5,
            )
        )
        color_idx += 1

    # =========================
    # Other indicators (NORMALIZED to price avg, OVERLAID on panel 0)
    # =========================
    for col in separate_indicators:
        series = df_plot[col]

        # Skip if empty / all NaN
        if series.isna().all():
            continue

        # Store original range for label
        series_clean = series.dropna()
        if len(series_clean) > 0:
            min_val = series_clean.min()
            max_val = series_clean.max()
            indicator_avg = series_clean.mean()
            
            # Get price range for normalization
            price_min = df_plot['Close'].min()
            price_max = df_plot['Close'].max()
            price_range = price_max - price_min
            
            # Target range: 10% of price range
            target_range = 1.1 * price_range
            
            # Calculate scaling factor to match price average
            if indicator_avg != 0 and max_val != min_val:
                # First scale to match average
                scale_factor = price_avg / indicator_avg
                normalized = series * scale_factor
                
                # Then compress to 10% of price range
                normalized_range = normalized.max() - normalized.min()
                if normalized_range > 0:
                    compression_factor = target_range / normalized_range
                    normalized = (normalized - normalized.mean()) * compression_factor + price_avg
                
                label = f"{col} [orig: {min_val:.2f} - {max_val:.2f}]"
            else:
                normalized = series
                label = f"{col} [orig: {min_val:.2f} - {max_val:.2f}]"
        else:
            label = col
            normalized = series

        apds.append(
            mpf.make_addplot(
                normalized,
                panel=0,  # OVERLAY on main candlestick panel
                label=label,
                color=colors[color_idx % len(colors)],
                secondary_y=False,
                alpha=0.5,
            )
        )
        color_idx += 1

    # =========================
    # Plot
    # =========================
    # Build kwargs conditionally
    plot_kwargs = {
        "data": df_plot,
        "type": "candle",
        "style": "charles",
        "figsize": (14, 8),
        "datetime_format": "%Y-%m-%d",
        "xrotation": 45,
        "returnfig": True,
    }
    
    # Only add addplot if we have indicators
    if len(apds) > 0:
        plot_kwargs["addplot"] = apds
    
    fig, axlist = mpf.plot(**plot_kwargs)
    
    # Add legend to main panel
    axlist[0].legend(loc='upper left', fontsize=8)

    return fig














