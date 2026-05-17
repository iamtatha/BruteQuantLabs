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


def calculate_supertrend(df, basic_upper_col='basic_upper', basic_lower_col='basic_lower', close_col='close'):
    """
    Calculate Supertrend indicator from basic upper and lower bands.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing OHLC data and basic bands
    basic_upper_col : str
        Column name for basic upper band
    basic_lower_col : str
        Column name for basic lower band
    close_col : str
        Column name for close price
    
    Returns:
    --------
    pd.DataFrame
        Original dataframe with added columns:
        - final_upper: Final upper band
        - final_lower: Final lower band
        - supertrend: Supertrend line
        - supertrend_direction: 1 for uptrend, -1 for downtrend
    """
    df = df.copy()
    
    # Initialize arrays with NaN
    final_upper = np.full(len(df), np.nan)
    final_lower = np.full(len(df), np.nan)
    supertrend = np.full(len(df), np.nan)
    direction = np.full(len(df), -1)  # -1 = DOWN, 1 = UP
    
    # Find first valid row (where basic bands are not NaN)
    valid_mask = ~(df[basic_upper_col].isna() | df[basic_lower_col].isna() | df[close_col].isna())
    
    if not valid_mask.any():
        # All values are NaN, return df with NaN columns
        df['final_upper'] = final_upper
        df['final_lower'] = final_lower
        df['supertrend'] = supertrend
        df['supertrend_direction'] = direction
        return df
    
    first_valid_idx = valid_mask.idxmax()
    first_valid_pos = df.index.get_loc(first_valid_idx)
    
    # Initialize first valid row
    final_upper[first_valid_pos] = df[basic_upper_col].iloc[first_valid_pos]
    final_lower[first_valid_pos] = df[basic_lower_col].iloc[first_valid_pos]
    supertrend[first_valid_pos] = final_upper[first_valid_pos]
    direction[first_valid_pos] = -1  # Start with downtrend
    
    # Calculate for each row starting from first valid + 1
    for i in range(first_valid_pos + 1, len(df)):
        # Skip if current row has NaN
        if pd.isna(df[basic_upper_col].iloc[i]) or pd.isna(df[basic_lower_col].iloc[i]) or pd.isna(df[close_col].iloc[i]):
            continue
        
        close_prev = df[close_col].iloc[i-1]
        close_curr = df[close_col].iloc[i]
        basic_upper_curr = df[basic_upper_col].iloc[i]
        basic_lower_curr = df[basic_lower_col].iloc[i]
        
        # Skip if previous values are NaN
        if pd.isna(final_upper[i-1]) or pd.isna(final_lower[i-1]):
            # Initialize this row as if it's the first
            final_upper[i] = basic_upper_curr
            final_lower[i] = basic_lower_curr
            supertrend[i] = final_upper[i]
            direction[i] = -1
            continue
        
        # Step 2: Calculate Final Bands
        # Final Upper
        if basic_upper_curr < final_upper[i-1] or close_prev > final_upper[i-1]:
            final_upper[i] = basic_upper_curr
        else:
            final_upper[i] = final_upper[i-1]
        
        # Final Lower
        if basic_lower_curr > final_lower[i-1] or close_prev < final_lower[i-1]:
            final_lower[i] = basic_lower_curr
        else:
            final_lower[i] = final_lower[i-1]
        
        # Step 3: Determine Supertrend and Direction
        # Check if trend should change
        if direction[i-1] == -1:  # Was in downtrend
            if close_curr > final_upper[i]:
                direction[i] = 1  # Switch to uptrend
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1  # Stay in downtrend
                supertrend[i] = final_upper[i]
        else:  # Was in uptrend
            if close_curr < final_lower[i]:
                direction[i] = -1  # Switch to downtrend
                supertrend[i] = final_upper[i]
            else:
                direction[i] = 1  # Stay in uptrend
                supertrend[i] = final_lower[i]
    
    # Add to dataframe
    df['final_upper'] = final_upper
    df['final_lower'] = final_lower
    df['supertrend'] = supertrend
    df['supertrend_direction'] = direction
    
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
        df = calculate_supertrend(df, basic_lower_col="supertrend_lower", basic_upper_col="supertrend_upper")

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










def plot_with_advanced_indicators(df, indicators=None):
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
    direction_indicators = []  # Add this

    for col in indicators:
        if col not in df_plot.columns:
            print(f"Warning: {col} not found in DataFrame columns.")
            continue

        # Direction indicators - special handling
        if 'direction' in col.lower():
            direction_indicators.append(col)
        # Heuristic: price-like indicators → overlay
        elif any(col.lower().startswith(key) for key in ["ema_", "sma_", "vwap"]) or \
        any(key in col.lower() for key in ["bb_upper", "bb_lower", "kc_upper", "kc_lower", "donchian", "supertrend"]):
            overlay_indicators.append(col)
        else:
            separate_indicators.append(col)
    print(direction_indicators)
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
    # Direction indicators (separate panel, NO normalization)
    # =========================
    panel_id = 1
    for col in direction_indicators:
        print(col)
        series = df_plot[col]
        
        if series.isna().all():
            continue
        
        series_clean = series.dropna()
        if len(series_clean) > 0:
            min_val = series_clean.min()
            max_val = series_clean.max()
            label = f"{col} [{min_val:.2f} - {max_val:.2f}]"
        else:
            label = col
        
        apds.append(
            mpf.make_addplot(
                series,
                panel=panel_id,
                label=label,
                color=colors[color_idx % len(colors)],
                alpha=0.7,
                secondary_y=False
            )
        )
        color_idx += 1
        panel_id += 1

    # =========================
    # Plot
    # =========================
    # Build kwargs conditionally
    plot_kwargs = {
        "data": df_plot,
        "type": "candle",
        "style": "charles",
        "figsize": (14, 10),  # Increase height for multiple panels
        "datetime_format": "%Y-%m-%d",
        "xrotation": 45,
        "returnfig": True,
        "panel_ratios": [3] + [1] * (panel_id - 1),  # Add this
}
    
    # Only add addplot if we have indicators
    if len(apds) > 0:
        plot_kwargs["addplot"] = apds
    
    fig, axlist = mpf.plot(**plot_kwargs)
    
    # Add legend to main panel
    axlist[0].legend(loc='upper left', fontsize=8)

    return fig











