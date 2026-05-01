import pandas as pd
import numpy as np
import mplfinance as mpf

# =========================
# 📈 TREND (ADVANCED)
# =========================

def add_ichimoku(df):
    high9 = df["high"].rolling(9).max()
    low9 = df["low"].rolling(9).min()

    high26 = df["high"].rolling(26).max()
    low26 = df["low"].rolling(26).min()

    high52 = df["high"].rolling(52).max()
    low52 = df["low"].rolling(52).min()

    df["tenkan"] = (high9 + low9) / 2
    df["kijun"] = (high26 + low26) / 2
    df["senkou_a"] = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
    df["senkou_b"] = ((high52 + low52) / 2).shift(26)
    df["chikou"] = df["close"].shift(-26)

    return df


def add_aroon(df, period=25):
    aroon_up = df["high"].rolling(period).apply(lambda x: np.argmax(x[::-1]) / period * 100)
    aroon_down = df["low"].rolling(period).apply(lambda x: np.argmin(x[::-1]) / period * 100)

    df["aroon_up"] = aroon_up
    df["aroon_down"] = aroon_down

    return df


def add_vortex(df, period=14):
    tr = np.maximum(df["high"] - df["low"],
                    np.maximum(abs(df["high"] - df["close"].shift()),
                               abs(df["low"] - df["close"].shift())))

    vm_plus = abs(df["high"] - df["low"].shift())
    vm_minus = abs(df["low"] - df["high"].shift())

    df["vortex_plus"] = vm_plus.rolling(period).sum() / tr.rolling(period).sum()
    df["vortex_minus"] = vm_minus.rolling(period).sum() / tr.rolling(period).sum()

    return df


def add_supertrend(df, period=10, multiplier=3):
    hl2 = (df["high"] + df["low"]) / 2

    tr = np.maximum(df["high"] - df["low"],
                    np.maximum(abs(df["high"] - df["close"].shift()),
                               abs(df["low"] - df["close"].shift())))

    atr = tr.rolling(period).mean()

    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    df["supertrend_upper"] = upper
    df["supertrend_lower"] = lower

    return df


# =========================
# ⚡ MOMENTUM (ADVANCED)
# =========================

def add_williams_r(df, period=14):
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()

    df["williams_r"] = -100 * (high_max - df["close"]) / (high_max - low_min + 1e-9)
    return df


def add_stoch_rsi(df, period=14):
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))

    min_rsi = rsi.rolling(period).min()
    max_rsi = rsi.rolling(period).max()

    df["stoch_rsi"] = (rsi - min_rsi) / (max_rsi - min_rsi + 1e-9)
    return df


def add_trix(df, period=15):
    ema1 = df["close"].ewm(span=period).mean()
    ema2 = ema1.ewm(span=period).mean()
    ema3 = ema2.ewm(span=period).mean()

    df["trix"] = ema3.pct_change()
    return df


def add_cci(df, period=20):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - np.mean(x))))

    df["cci"] = (tp - sma) / (0.015 * mad + 1e-9)
    return df


# =========================
# 📊 VOLUME (ADVANCED)
# =========================

def add_chaikin_money_flow(df, period=20):
    mf_multiplier = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (df["high"] - df["low"] + 1e-9)
    mf_volume = mf_multiplier * df["volume"]

    df["cmf"] = mf_volume.rolling(period).sum() / df["volume"].rolling(period).sum()
    return df


def add_volume_oscillator(df, short=14, long=28):
    short_ma = df["volume"].rolling(short).mean()
    long_ma = df["volume"].rolling(long).mean()

    df["vol_osc"] = (short_ma - long_ma) / (long_ma + 1e-9)
    return df


# =========================
# 📉 VOLATILITY (ADVANCED)
# =========================

def add_keltner_channel(df, period=20):
    ema = df["close"].ewm(span=period).mean()

    tr = np.maximum(df["high"] - df["low"],
                    np.maximum(abs(df["high"] - df["close"].shift()),
                               abs(df["low"] - df["close"].shift())))

    atr = tr.rolling(period).mean()

    df["kc_upper"] = ema + 2 * atr
    df["kc_lower"] = ema - 2 * atr

    return df


def add_donchian_channel(df, period=20):
    df["donchian_upper"] = df["high"].rolling(period).max()
    df["donchian_lower"] = df["low"].rolling(period).min()
    return df


# =========================
# 🔁 ADVANCED MOVING AVERAGES
# =========================

def add_hma(df, period=20):
    wma_half = df["close"].rolling(period // 2).mean()
    wma_full = df["close"].rolling(period).mean()

    raw = 2 * wma_half - wma_full
    df["hma"] = raw.rolling(int(np.sqrt(period))).mean()

    return df


def add_kama(df, period=10):
    change = abs(df["close"] - df["close"].shift(period))
    volatility = df["close"].diff().abs().rolling(period).sum()

    er = change / (volatility + 1e-9)

    fast = 2 / (2 + 1)
    slow = 2 / (30 + 1)

    sc = (er * (fast - slow) + slow) ** 2

    kama = [df["close"].iloc[0]]

    for i in range(1, len(df)):
        kama.append(kama[-1] + sc.iloc[i] * (df["close"].iloc[i] - kama[-1]))

    df["kama"] = kama
    return df


# =========================
# 🚀 MASTER FUNCTION
# =========================

def add_advanced_indicators(df, indicators=None):
    df = df.copy()

    if indicators is None:
        indicators = [
            "ichimoku", "aroon", "vortex", "supertrend",
            "williams_r", "stoch_rsi", "trix", "cci",
            "cmf", "volume_osc",
            "keltner", "donchian",
            "hma", "kama"
        ]

    if "ichimoku" in indicators:
        df = add_ichimoku(df)

    if "aroon" in indicators:
        df = add_aroon(df)

    if "vortex" in indicators:
        df = add_vortex(df)

    if "supertrend" in indicators:
        df = add_supertrend(df)

    if "williams_r" in indicators:
        df = add_williams_r(df)

    if "stoch_rsi" in indicators:
        df = add_stoch_rsi(df)

    if "trix" in indicators:
        df = add_trix(df)

    if "cci" in indicators:
        df = add_cci(df)

    if "cmf" in indicators:
        df = add_chaikin_money_flow(df)

    if "volume_osc" in indicators:
        df = add_volume_oscillator(df)

    if "keltner" in indicators:
        df = add_keltner_channel(df)

    if "donchian" in indicators:
        df = add_donchian_channel(df)

    if "hma" in indicators:
        df = add_hma(df)

    if "kama" in indicators:
        df = add_kama(df)

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











