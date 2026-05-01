import pandas as pd
import numpy as np
import mplfinance as mpf
from scipy import signal, stats


def detect_candles(df):
    df = df.copy()

    # --- Basics ---
    df["body"] = (df["close"] - df["open"]).abs()
    df["range"] = (df["high"] - df["low"]).replace(0, 1e-9)

    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    df["body_ratio"] = df["body"] / df["range"]
    df["upper_wick_ratio"] = df["upper_wick"] / df["range"]
    df["lower_wick_ratio"] = df["lower_wick"] / df["range"]

    prev = df.shift(1)
    prev2 = df.shift(2)


    # --- CONTEXT FEATURES ---

    # EMA (trend)
    df["ema20"] = df["close"].ewm(span=20).mean()

    # Trend slope (normalized)
    df["ema_slope"] = df["ema20"].diff()

    # Trend direction
    df["uptrend"] = (df["close"] > df["ema20"]) & (df["ema_slope"] > 0)
    df["downtrend"] = (df["close"] < df["ema20"]) & (df["ema_slope"] < 0)

    # Recent support/resistance (rolling window)
    window = 20
    df["recent_low"] = df["low"].rolling(window).min()
    df["recent_high"] = df["high"].rolling(window).max()

    # Distance to zones
    df["near_support"] = (df["close"] <= df["recent_low"] * 1.02)
    df["near_resistance"] = (df["close"] >= df["recent_high"] * 0.98)

    # =========================
    # 🕯️ SINGLE CANDLE PATTERNS
    # =========================

    # Long Day (strong body)
    df["long_day"] = df["body_ratio"] > 0.7

    # Short Day
    df["short_day"] = df["body_ratio"] < 0.25

    # Doji (strict)
    df["doji"] = df["body_ratio"] < 0.05

    # Gravestone Doji
    df["gravestone_doji"] = (
        (df["body_ratio"] < 0.05) &
        (df["lower_wick_ratio"] < 0.05) &
        (df["upper_wick_ratio"] > 0.6)
    )

    # Dragonfly Doji
    df["dragonfly_doji"] = (
        (df["body_ratio"] < 0.05) &
        (df["upper_wick_ratio"] < 0.05) &
        (df["lower_wick_ratio"] > 0.6)
    )

    # Long Legged Doji
    df["long_legged_doji"] = (
        (df["body_ratio"] < 0.05) &
        (df["upper_wick_ratio"] > 0.4) &
        (df["lower_wick_ratio"] > 0.4)
    )

    # Hammer (strict)
    df["hammer"] = (
        (df["lower_wick"] > 2.5 * df["body"]) &
        (df["upper_wick"] < 0.2 * df["body"]) &
        (df["body_ratio"] < 0.4)
    )

    df["hammer_valid"] = (
        df["hammer"] &
        df["downtrend"] &
        df["near_support"]
    )

    # Hanging Man (same shape, context matters later)
    df["hanging_man"] = df["hammer"]

    df["hanging_man_valid"] = (
        df["hanging_man"] &
        df["uptrend"] &
        df["near_resistance"]
    )

    # Shooting Star
    df["shooting_star"] = (
        (df["upper_wick"] > 2.5 * df["body"]) &
        (df["lower_wick"] < 0.2 * df["body"]) &
        (df["body_ratio"] < 0.4)
    )

    df["shooting_star_valid"] = (
        df["shooting_star"] &
        df["uptrend"] &
        df["near_resistance"]
    )

    # =========================
    # 🕯️ DOUBLE CANDLE PATTERNS
    # =========================

    # Bullish Engulfing (strict)
    df["bullish_engulfing"] = (
        (prev["close"] < prev["open"]) &
        (df["close"] > df["open"]) &
        (df["open"] < prev["close"]) &
        (df["close"] > prev["open"]) &
        (df["body"] > prev["body"] * 1.2)
    )

    # Bearish Engulfing
    df["bearish_engulfing"] = (
        (prev["close"] > prev["open"]) &
        (df["close"] < df["open"]) &
        (df["open"] > prev["close"]) &
        (df["close"] < prev["open"]) &
        (df["body"] > prev["body"] * 1.2)
    )

    df["bullish_engulfing_valid"] = (
        df["bullish_engulfing"] &
        df["downtrend"]
    )

    df["bearish_engulfing_valid"] = (
        df["bearish_engulfing"] &
        df["uptrend"]
    )

    # Piercing Line
    df["piercing_line"] = (
        (prev["close"] < prev["open"]) &
        (df["close"] > df["open"]) &
        (df["open"] < prev["low"]) &
        (df["close"] > (prev["open"] + prev["close"]) / 2) &
        (df["close"] < prev["open"])
    )

    # Dark Cloud Cover
    df["dark_cloud_cover"] = (
        (prev["close"] > prev["open"]) &
        (df["close"] < df["open"]) &
        (df["open"] > prev["high"]) &
        (df["close"] < (prev["open"] + prev["close"]) / 2) &
        (df["close"] > prev["open"])
    )

    # =========================
    # 🕯️ TRIPLE CANDLE PATTERNS
    # =========================

    # Morning Star (strict)
    df["morning_star"] = (
        (prev2["close"] < prev2["open"]) &                      # strong red
        (prev["body_ratio"] < 0.3) &                            # small body
        (df["close"] > df["open"]) &                            # green
        (df["close"] > (prev2["open"] + prev2["close"]) / 2) &  # recovery
        (prev["low"] < prev2["low"])                            # gap-like effect
    )

    # Evening Star
    df["evening_star"] = (
        (prev2["close"] > prev2["open"]) &
        (prev["body_ratio"] < 0.3) &
        (df["close"] < df["open"]) &
        (df["close"] < (prev2["open"] + prev2["close"]) / 2) &
        (prev["high"] > prev2["high"])
    )

    df["morning_star_valid"] = df["morning_star"] & df["downtrend"]
    df["evening_star_valid"] = df["evening_star"] & df["uptrend"]

    return df



def detect_chart_patterns(df, window=5):
    df = df.copy().reset_index(drop=True)

    # =========================
    # SWING POINTS
    # =========================
    df["swing_high"] = df["high"][
        (df["high"] == df["high"].rolling(window, center=True).max())
    ]

    df["swing_low"] = df["low"][
        (df["low"] == df["low"].rolling(window, center=True).min())
    ]

    # Initialize columns
    pattern_cols = [
        "double_top", "double_bottom",
        "head_and_shoulders", "inv_head_and_shoulders",
        "rising_wedge", "falling_wedge",
        "rounding_bottom",
        "sym_triangle", "asc_triangle",
        "flag", "rectangle", "channel",
        "cup_handle"
    ]

    for col in pattern_cols:
        df[col] = False

    # =========================
    # LOOP (only last region)
    # =========================
    for i in range(30, len(df)):

        sub = df.iloc[:i]

        highs = sub.dropna(subset=["swing_high"])
        lows = sub.dropna(subset=["swing_low"])

        if len(highs) < 3 or len(lows) < 3:
            continue

        last_highs = highs.tail(3)["swing_high"].values
        last_lows = lows.tail(3)["swing_low"].values

        # ----------------------
        # DOUBLE TOP / BOTTOM
        # ----------------------
        if len(last_highs) >= 2:
            if abs(last_highs[-1] - last_highs[-2]) / last_highs[-2] < 0.02:
                df.loc[i, "double_top"] = True

        if len(last_lows) >= 2:
            if abs(last_lows[-1] - last_lows[-2]) / last_lows[-2] < 0.02:
                df.loc[i, "double_bottom"] = True

        # ----------------------
        # HEAD & SHOULDERS
        # ----------------------
        if len(last_highs) >= 3:
            h1, h2, h3 = last_highs[-3:]
            if h2 > h1 and h2 > h3 and abs(h1 - h3)/h2 < 0.05:
                df.loc[i, "head_and_shoulders"] = True

        if len(last_lows) >= 3:
            l1, l2, l3 = last_lows[-3:]
            if l2 < l1 and l2 < l3 and abs(l1 - l3)/abs(l2) < 0.05:
                df.loc[i, "inv_head_and_shoulders"] = True

        # ----------------------
        # WEDGES
        # ----------------------
        if len(highs) >= 5 and len(lows) >= 5:
            h = highs.tail(5)["swing_high"].values
            l = lows.tail(5)["swing_low"].values

            high_slope = np.polyfit(range(len(h)), h, 1)[0]
            low_slope = np.polyfit(range(len(l)), l, 1)[0]

            if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
                df.loc[i, "rising_wedge"] = True

            if high_slope < 0 and low_slope < 0 and low_slope < high_slope:
                df.loc[i, "falling_wedge"] = True

        # ----------------------
        # TRIANGLES
        # ----------------------
        if len(highs) >= 5 and len(lows) >= 5:
            h = highs.tail(5)["swing_high"].values
            l = lows.tail(5)["swing_low"].values

            high_slope = np.polyfit(range(5), h, 1)[0]
            low_slope = np.polyfit(range(5), l, 1)[0]

            if high_slope < 0 and low_slope > 0:
                df.loc[i, "sym_triangle"] = True

            if abs(high_slope) < 0.01 and low_slope > 0:
                df.loc[i, "asc_triangle"] = True

        # ----------------------
        # RECTANGLE / CHANNEL
        # ----------------------
        if len(highs) >= 5 and len(lows) >= 5:
            h = highs.tail(5)["swing_high"]
            l = lows.tail(5)["swing_low"]

            if h.std() < 0.02 * sub["close"].mean():
                df.loc[i, "rectangle"] = True

            high_slope = np.polyfit(range(5), h, 1)[0]
            low_slope = np.polyfit(range(5), l, 1)[0]

            if abs(high_slope - low_slope) < 0.01:
                df.loc[i, "channel"] = True

        # ----------------------
        # FLAG
        # ----------------------
        recent = sub.tail(20)
        move = recent["close"].iloc[-1] - recent["close"].iloc[0]

        if abs(move) > sub["close"].std():
            if recent["high"].std() < sub["close"].std() * 0.5:
                df.loc[i, "flag"] = True

        # ----------------------
        # ROUNDING BOTTOM
        # ----------------------
        closes = sub["close"].tail(30).values
        if len(closes) >= 30:
            x = np.arange(len(closes))
            coeffs = np.polyfit(x, closes, 2)
            if coeffs[0] > 0:
                df.loc[i, "rounding_bottom"] = True

        # ----------------------
        # CUP & HANDLE
        # ----------------------
        if len(closes) >= 30:
            mid = len(closes) // 2
            left = closes[:mid]
            right = closes[mid:]

            if min(left) == min(closes) and right[-1] > left[0]:
                df.loc[i, "cup_handle"] = True

    return df






def detect_candles_claude(df):
    """
    Improved candlestick pattern detection with confidence scoring.
    
    Improvements:
    - Better context features (volatility, momentum, trend strength)
    - Confidence scores (0-1) for each pattern based on pattern quality
    - Stricter validation rules with adaptive thresholds
    - Additional patterns (Morning/Evening Engulfing, Harami, etc.)
    
    Returns DataFrame with pattern columns + confidence columns
    """
    df = df.copy()
    
    # =========================
    # CANDLE ANATOMY
    # =========================
    df["body"] = (df["close"] - df["open"]).abs()
    df["range"] = (df["high"] - df["low"]).replace(0, 1e-9)
    
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    
    df["body_ratio"] = df["body"] / df["range"]
    df["upper_wick_ratio"] = df["upper_wick"] / df["range"]
    df["lower_wick_ratio"] = df["lower_wick"] / df["range"]
    
    df["is_bullish"] = df["close"] > df["open"]
    df["is_bearish"] = df["close"] < df["open"]
    
    prev = df.shift(1)
    prev2 = df.shift(2)
    
    # =========================
    # IMPROVED CONTEXT FEATURES
    # =========================
    
    # Trend (EMA + slope)
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema_slope"] = df["ema20"].diff()
    
    # Trend strength (normalized slope)
    atr14 = df["range"].rolling(14).mean()
    df["ema_slope_normalized"] = df["ema_slope"] / atr14
    
    df["uptrend"] = (df["close"] > df["ema20"]) & (df["ema_slope"] > 0)
    df["downtrend"] = (df["close"] < df["ema20"]) & (df["ema_slope"] < 0)
    
    # Volatility (ATR-based, normalized)
    df["atr14"] = atr14
    df["volatility"] = df["atr14"] / df["close"] * 100  # % volatility
    
    # Support / Resistance (dynamic zones)
    window = 20
    df["recent_low"] = df["low"].rolling(window).min()
    df["recent_high"] = df["high"].rolling(window).max()
    df["recent_mid"] = (df["recent_low"] + df["recent_high"]) / 2
    
    # Distance to zones (as % of range)
    recent_range = df["recent_high"] - df["recent_low"]
    df["dist_to_support"] = (df["close"] - df["recent_low"]) / recent_range * 100
    df["dist_to_resistance"] = (df["recent_high"] - df["close"]) / recent_range * 100
    
    df["near_support"] = df["dist_to_support"] < 10  # Bottom 10% of range
    df["near_resistance"] = df["dist_to_resistance"] < 10  # Top 10% of range
    
    # Momentum (RSI-inspired, normalized price change)
    df["momentum"] = df["close"].diff() / df["atr14"]
    df["momentum_ma"] = df["momentum"].rolling(5).mean()
    
    # =========================
    # HELPER FUNCTION: Confidence Scorer
    # =========================
    def confidence_score(*conditions):
        """
        Combine multiple boolean conditions into a confidence score (0-1).
        Each True condition adds equal weight.
        """
        valid_conditions = [c for c in conditions if c is not None]
        if not valid_conditions:
            return 0.0
        score = sum(valid_conditions) / len(valid_conditions)
        return float(score)
    
    # =========================
    # SINGLE CANDLE PATTERNS
    # =========================
    
    # Long Day (strong body)
    df["long_day"] = df["body_ratio"] > 0.7
    df["long_day_conf"] = 0.0
    mask = df["long_day"]
    df.loc[mask, "long_day_conf"] = (
        (df.loc[mask, "body_ratio"] - 0.7) / 0.3  # How much above 0.7
    ).clip(0, 1)
    
    # Short Day / Doji variants
    df["short_day"] = df["body_ratio"] < 0.25
    df["short_day_conf"] = 0.0
    mask = df["short_day"]
    df.loc[mask, "short_day_conf"] = 1 - df.loc[mask, "body_ratio"] / 0.25
    
    # Doji (very small body, balanced wicks)
    df["doji"] = df["body_ratio"] < 0.05
    df["doji_conf"] = 0.0
    mask = df["doji"]
    wick_balance = (
        1 - np.abs(df.loc[mask, "upper_wick_ratio"] - df.loc[mask, "lower_wick_ratio"])
    )
    df.loc[mask, "doji_conf"] = (
        (1 - df.loc[mask, "body_ratio"] / 0.05) * 0.6 +  # 60% = body smallness
        wick_balance * 0.4  # 40% = wick balance
    ).clip(0, 1)
    
    # Gravestone Doji (small body, no lower wick, big upper wick)
    df["gravestone_doji"] = (
        (df["body_ratio"] < 0.05) &
        (df["lower_wick_ratio"] < 0.05) &
        (df["upper_wick_ratio"] > 0.6)
    )
    df["gravestone_doji_conf"] = 0.0
    mask = df["gravestone_doji"]
    df.loc[mask, "gravestone_doji_conf"] = (
        (1 - df.loc[mask, "body_ratio"] / 0.05) * 0.3 +
        (1 - df.loc[mask, "lower_wick_ratio"] / 0.05) * 0.3 +
        (df.loc[mask, "upper_wick_ratio"] - 0.6) / 0.4 * 0.4
    ).clip(0, 1)
    
    # Dragonfly Doji (small body, no upper wick, big lower wick)
    df["dragonfly_doji"] = (
        (df["body_ratio"] < 0.05) &
        (df["upper_wick_ratio"] < 0.05) &
        (df["lower_wick_ratio"] > 0.6)
    )
    df["dragonfly_doji_conf"] = 0.0
    mask = df["dragonfly_doji"]
    df.loc[mask, "dragonfly_doji_conf"] = (
        (1 - df.loc[mask, "body_ratio"] / 0.05) * 0.3 +
        (1 - df.loc[mask, "upper_wick_ratio"] / 0.05) * 0.3 +
        (df.loc[mask, "lower_wick_ratio"] - 0.6) / 0.4 * 0.4
    ).clip(0, 1)
    
    # Long Legged Doji
    df["long_legged_doji"] = (
        (df["body_ratio"] < 0.05) &
        (df["upper_wick_ratio"] > 0.4) &
        (df["lower_wick_ratio"] > 0.4)
    )
    df["long_legged_doji_conf"] = 0.0
    mask = df["long_legged_doji"]
    wick_balance = 1 - np.abs(df.loc[mask, "upper_wick_ratio"] - df.loc[mask, "lower_wick_ratio"]) / 0.8
    df.loc[mask, "long_legged_doji_conf"] = (
        (1 - df.loc[mask, "body_ratio"] / 0.05) * 0.4 +
        wick_balance * 0.6
    ).clip(0, 1)
    
    # Hammer (strong reversal at support)
    df["hammer"] = (
        (df["lower_wick"] > 2.5 * df["body"]) &
        (df["upper_wick"] < 0.2 * df["body"]) &
        (df["body_ratio"] < 0.4)
    )
    df["hammer_conf"] = 0.0
    mask = df["hammer"]
    wick_ratio = df.loc[mask, "lower_wick"] / df.loc[mask, "body"].clip(lower=0.01)
    df.loc[mask, "hammer_conf"] = (
        (wick_ratio.clip(upper=5) / 5) * 0.5 +
        (1 - df.loc[mask, "upper_wick_ratio"] / 0.2) * 0.25 +
        (1 - df.loc[mask, "body_ratio"] / 0.4) * 0.25
    ).clip(0, 1)
    
    # Hammer validation (context matters)
    df["hammer_valid"] = False
    df["hammer_valid_conf"] = 0.0
    mask = df["hammer"]
    df.loc[mask, "hammer_valid"] = (
        df.loc[mask, "downtrend"] &
        df.loc[mask, "near_support"]
    )
    df.loc[mask, "hammer_valid_conf"] = (
        df.loc[mask, "hammer_conf"] * 0.5 +
        df.loc[mask, "downtrend"].astype(float) * 0.25 +
        df.loc[mask, "near_support"].astype(float) * 0.25
    ).clip(0, 1)
    
    # Hanging Man (same shape as hammer, opposite context)
    df["hanging_man"] = df["hammer"]
    df["hanging_man_conf"] = df["hammer_conf"]
    
    df["hanging_man_valid"] = False
    df["hanging_man_valid_conf"] = 0.0
    mask = df["hanging_man"]
    df.loc[mask, "hanging_man_valid"] = (
        df.loc[mask, "uptrend"] &
        df.loc[mask, "near_resistance"]
    )
    df.loc[mask, "hanging_man_valid_conf"] = (
        df.loc[mask, "hanging_man_conf"] * 0.5 +
        df.loc[mask, "uptrend"].astype(float) * 0.25 +
        df.loc[mask, "near_resistance"].astype(float) * 0.25
    ).clip(0, 1)
    
    # Shooting Star (opposite of hammer: big upper wick)
    df["shooting_star"] = (
        (df["upper_wick"] > 2.5 * df["body"]) &
        (df["lower_wick"] < 0.2 * df["body"]) &
        (df["body_ratio"] < 0.4)
    )
    df["shooting_star_conf"] = 0.0
    mask = df["shooting_star"]
    wick_ratio = df.loc[mask, "upper_wick"] / df.loc[mask, "body"].clip(lower=0.01)
    df.loc[mask, "shooting_star_conf"] = (
        (wick_ratio.clip(upper=5) / 5) * 0.5 +
        (1 - df.loc[mask, "lower_wick_ratio"] / 0.2) * 0.25 +
        (1 - df.loc[mask, "body_ratio"] / 0.4) * 0.25
    ).clip(0, 1)
    
    df["shooting_star_valid"] = False
    df["shooting_star_valid_conf"] = 0.0
    mask = df["shooting_star"]
    df.loc[mask, "shooting_star_valid"] = (
        df.loc[mask, "uptrend"] &
        df.loc[mask, "near_resistance"]
    )
    df.loc[mask, "shooting_star_valid_conf"] = (
        df.loc[mask, "shooting_star_conf"] * 0.5 +
        df.loc[mask, "uptrend"].astype(float) * 0.25 +
        df.loc[mask, "near_resistance"].astype(float) * 0.25
    ).clip(0, 1)
    
    # =========================
    # DOUBLE CANDLE PATTERNS
    # =========================
    
    # Bullish Engulfing
    df["bullish_engulfing"] = (
        (prev["close"] < prev["open"]) &  # Previous bearish
        (df["close"] > df["open"]) &  # Current bullish
        (df["open"] <= prev["close"]) &  # Opens at/below prev close
        (df["close"] >= prev["open"]) &  # Closes above prev open
        (df["body"] > prev["body"] * 1.1)  # Larger body
    )
    df["bullish_engulfing_conf"] = 0.0
    mask = df["bullish_engulfing"]
    engulf_ratio = df.loc[mask, "body"] / (prev.loc[mask, "body"] + 1e-9)
    df.loc[mask, "bullish_engulfing_conf"] = (
        (engulf_ratio.clip(upper=3) / 3) * 0.5 +
        (df.loc[mask, "body_ratio"] / 0.8).clip(0, 1) * 0.3 +
        ((prev.loc[mask, "body_ratio"] < 0.3).astype(float)) * 0.2
    ).clip(0, 1)
    
    df["bullish_engulfing_valid"] = False
    df["bullish_engulfing_valid_conf"] = 0.0
    mask = df["bullish_engulfing"]
    df.loc[mask, "bullish_engulfing_valid"] = (
        df.loc[mask, "downtrend"]
    )
    df.loc[mask, "bullish_engulfing_valid_conf"] = (
        df.loc[mask, "bullish_engulfing_conf"] * 0.7 +
        df.loc[mask, "downtrend"].astype(float) * 0.3
    ).clip(0, 1)
    
    # Bearish Engulfing
    df["bearish_engulfing"] = (
        (prev["close"] > prev["open"]) &
        (df["close"] < df["open"]) &
        (df["open"] >= prev["close"]) &
        (df["close"] <= prev["open"]) &
        (df["body"] > prev["body"] * 1.1)
    )
    df["bearish_engulfing_conf"] = 0.0
    mask = df["bearish_engulfing"]
    engulf_ratio = df.loc[mask, "body"] / (prev.loc[mask, "body"] + 1e-9)
    df.loc[mask, "bearish_engulfing_conf"] = (
        (engulf_ratio.clip(upper=3) / 3) * 0.5 +
        (df.loc[mask, "body_ratio"] / 0.8).clip(0, 1) * 0.3 +
        ((prev.loc[mask, "body_ratio"] < 0.3).astype(float)) * 0.2
    ).clip(0, 1)
    
    df["bearish_engulfing_valid"] = False
    df["bearish_engulfing_valid_conf"] = 0.0
    mask = df["bearish_engulfing"]
    df.loc[mask, "bearish_engulfing_valid"] = (
        df.loc[mask, "uptrend"]
    )
    df.loc[mask, "bearish_engulfing_valid_conf"] = (
        df.loc[mask, "bearish_engulfing_conf"] * 0.7 +
        df.loc[mask, "uptrend"].astype(float) * 0.3
    ).clip(0, 1)
    
    # Harami (opposite of engulfing: smaller body inside previous)
    df["bullish_harami"] = (
        (prev["close"] < prev["open"]) &  # Previous bearish
        (df["close"] > df["open"]) &  # Current bullish
        (df["open"] > prev["close"]) &  # Opens above prev close
        (df["close"] < prev["open"]) &  # Closes below prev open
        (df["body"] < prev["body"] * 0.7)  # Smaller body
    )
    df["bullish_harami_conf"] = 0.0
    mask = df["bullish_harami"]
    harami_ratio = (prev.loc[mask, "body"] - df.loc[mask, "body"]) / (prev.loc[mask, "body"] + 1e-9)
    df.loc[mask, "bullish_harami_conf"] = (
        (harami_ratio.clip(0, 1)) * 0.5 +
        (df.loc[mask, "body_ratio"] / 0.5).clip(0, 1) * 0.3 +
        ((prev.loc[mask, "body_ratio"] > 0.5).astype(float)) * 0.2
    ).clip(0, 1)
    
    # Piercing Line (bullish, gap down then strong recovery)
    df["piercing_line"] = (
        (prev["close"] < prev["open"]) &  # Bearish candle
        (df["close"] > df["open"]) &  # Bullish candle
        (df["open"] < prev["low"]) &  # Opens below prev low (gap)
        (df["close"] > (prev["open"] + prev["close"]) / 2) &  # Closes above midpoint
        (df["close"] <= prev["open"]) &  # But below prev open
        (df["body_ratio"] > 0.5)  # Good body
    )
    df["piercing_line_conf"] = 0.0
    mask = df["piercing_line"]
    penetration = (df.loc[mask, "close"] - (prev.loc[mask, "open"] + prev.loc[mask, "close"]) / 2) / (
        (prev.loc[mask, "open"] - prev.loc[mask, "close"]).abs() + 1e-9
    )
    df.loc[mask, "piercing_line_conf"] = (
        (penetration.clip(0, 0.5) / 0.5) * 0.5 +
        (df.loc[mask, "body_ratio"] / 0.8).clip(0, 1) * 0.5
    ).clip(0, 1)
    
    # Dark Cloud Cover (bearish version of piercing line)
    df["dark_cloud_cover"] = (
        (prev["close"] > prev["open"]) &
        (df["close"] < df["open"]) &
        (df["open"] > prev["high"]) &
        (df["close"] < (prev["open"] + prev["close"]) / 2) &
        (df["close"] >= prev["open"]) &
        (df["body_ratio"] > 0.5)
    )
    df["dark_cloud_cover_conf"] = 0.0
    mask = df["dark_cloud_cover"]
    penetration = ((prev.loc[mask, "open"] + prev.loc[mask, "close"]) / 2 - df.loc[mask, "close"]) / (
        (prev.loc[mask, "close"] - prev.loc[mask, "open"]).abs() + 1e-9
    )
    df.loc[mask, "dark_cloud_cover_conf"] = (
        (penetration.clip(0, 0.5) / 0.5) * 0.5 +
        (df.loc[mask, "body_ratio"] / 0.8).clip(0, 1) * 0.5
    ).clip(0, 1)
    
    # =========================
    # TRIPLE CANDLE PATTERNS
    # =========================
    
    # Morning Star (bullish reversal: down, doji-like, up)
    df["morning_star"] = (
        (prev2["close"] < prev2["open"]) &  # Strong bearish
        (prev["body_ratio"] < 0.3) &  # Small body (doji-like)
        (prev["low"] < prev2["low"]) &  # Continues down
        (df["close"] > df["open"]) &  # Reverses up
        (df["close"] > (prev2["open"] + prev2["close"]) / 2)  # Strong recovery
    )
    df["morning_star_conf"] = 0.0
    mask = df["morning_star"]
    recovery = (df.loc[mask, "close"] - (prev2.loc[mask, "open"] + prev2.loc[mask, "close"]) / 2) / (
        (prev2.loc[mask, "open"] - prev2.loc[mask, "close"]).abs() + 1e-9
    )
    df.loc[mask, "morning_star_conf"] = (
        ((prev2.loc[mask, "body_ratio"] > 0.5).astype(float)) * 0.3 +
        ((prev.loc[mask, "body_ratio"] < 0.3).astype(float)) * 0.3 +
        (recovery.clip(0, 1)) * 0.4
    ).clip(0, 1)
    
    df["morning_star_valid"] = df["morning_star"] & df["downtrend"]
    df["morning_star_valid_conf"] = (
        df["morning_star_conf"] * 0.7 +
        df["downtrend"].astype(float) * 0.3
    ).clip(0, 1)
    
    # Evening Star (bearish version)
    df["evening_star"] = (
        (prev2["close"] > prev2["open"]) &
        (prev["body_ratio"] < 0.3) &
        (prev["high"] > prev2["high"]) &
        (df["close"] < df["open"]) &
        (df["close"] < (prev2["open"] + prev2["close"]) / 2)
    )
    df["evening_star_conf"] = 0.0
    mask = df["evening_star"]
    decline = ((prev2.loc[mask, "open"] + prev2.loc[mask, "close"]) / 2 - df.loc[mask, "close"]) / (
        (prev2.loc[mask, "close"] - prev2.loc[mask, "open"]).abs() + 1e-9
    )
    df.loc[mask, "evening_star_conf"] = (
        ((prev2.loc[mask, "body_ratio"] > 0.5).astype(float)) * 0.3 +
        ((prev.loc[mask, "body_ratio"] < 0.3).astype(float)) * 0.3 +
        (decline.clip(0, 1)) * 0.4
    ).clip(0, 1)
    
    df["evening_star_valid"] = df["evening_star"] & df["uptrend"]
    df["evening_star_valid_conf"] = (
        df["evening_star_conf"] * 0.7 +
        df["uptrend"].astype(float) * 0.3
    ).clip(0, 1)
    
    return df


def detect_chart_patterns_claude(df, window=5):
    """
    Improved chart pattern detection with confidence scoring.
    
    Improvements:
    - Better swing point detection (scipy.signal)
    - Pattern-specific confidence metrics
    - Multiple recent patterns tracked (not just latest)
    - Better wedge/triangle/flag detection
    - Stricter validation rules
    
    Returns DataFrame with pattern + confidence columns
    """
    df = df.copy().reset_index(drop=True)
    
    # =========================
    # IMPROVED SWING POINT DETECTION
    # =========================
    high_indices = signal.argrelextrema(df["high"].values, np.greater_equal, order=window)[0]
    low_indices = signal.argrelextrema(df["low"].values, np.less_equal, order=window)[0]
    
    df["swing_high_idx"] = np.nan
    df["swing_high"] = np.nan
    df.loc[high_indices, "swing_high"] = df.loc[high_indices, "high"]
    df.loc[high_indices, "swing_high_idx"] = high_indices
    
    df["swing_low_idx"] = np.nan
    df["swing_low"] = np.nan
    df.loc[low_indices, "swing_low"] = df.loc[low_indices, "low"]
    df.loc[low_indices, "swing_low_idx"] = low_indices
    
    # Initialize pattern columns
    pattern_cols = [
        "double_top", "double_bottom",
        "head_and_shoulders", "inv_head_and_shoulders",
        "rising_wedge", "falling_wedge",
        "rounding_bottom",
        "sym_triangle", "asc_triangle", "desc_triangle",
        "flag", "rectangle", "channel",
        "cup_handle"
    ]
    
    for col in pattern_cols:
        df[col] = False
        df[f"{col}_conf"] = 0.0
    
    # Get recent swings
    highs = df.dropna(subset=["swing_high"])
    lows = df.dropna(subset=["swing_low"])
    
    # =========================
    # LOOP THROUGH RECENT DATA
    # =========================
    for i in range(30, len(df)):
        sub = df.iloc[:i+1]
        
        highs = sub.dropna(subset=["swing_high"])
        lows = sub.dropna(subset=["swing_low"])
        
        if len(highs) < 2 or len(lows) < 2:
            continue
        
        # Get last few swings
        last_highs_vals = highs.tail(4)["swing_high"].values
        last_lows_vals = lows.tail(4)["swing_low"].values
        
        current_price = df.loc[i, "close"]
        
        # ----------------------
        # DOUBLE TOP / BOTTOM
        # ----------------------
        if len(last_highs_vals) >= 2:
            h1, h2 = last_highs_vals[-2:]
            diff_ratio = abs(h1 - h2) / h1
            
            if diff_ratio < 0.02:
                df.loc[i, "double_top"] = True
                # Confidence: tighter match + price breaking down
                breakout = min((0.02 - diff_ratio) / 0.02, 1.0)
                price_factor = 1.0 if current_price < min(h1, h2) else 0.5
                df.loc[i, "double_top_conf"] = (breakout * 0.5 + price_factor * 0.5)
        
        if len(last_lows_vals) >= 2:
            l1, l2 = last_lows_vals[-2:]
            diff_ratio = abs(l1 - l2) / l1
            
            if diff_ratio < 0.02:
                df.loc[i, "double_bottom"] = True
                breakout = min((0.02 - diff_ratio) / 0.02, 1.0)
                price_factor = 1.0 if current_price > max(l1, l2) else 0.5
                df.loc[i, "double_bottom_conf"] = (breakout * 0.5 + price_factor * 0.5)
        
        # ----------------------
        # HEAD & SHOULDERS
        # ----------------------
        if len(last_highs_vals) >= 3:
            h1, h2, h3 = last_highs_vals[-3:]
            shoulders_similar = abs(h1 - h3) / h2 < 0.05
            head_higher = h2 > h1 and h2 > h3
            
            if shoulders_similar and head_higher:
                df.loc[i, "head_and_shoulders"] = True
                shoulder_match = 1.0 - (abs(h1 - h3) / h2)
                head_prominence = (h2 - (h1 + h3) / 2) / ((h1 + h3) / 2)
                df.loc[i, "head_and_shoulders_conf"] = (
                    shoulder_match * 0.5 + min(head_prominence / 0.15, 1.0) * 0.5
                ).clip(0, 1)
        
        if len(last_lows_vals) >= 3:
            l1, l2, l3 = last_lows_vals[-3:]
            shoulders_similar = abs(l1 - l3) / l1 < 0.05
            head_lower = l2 < l1 and l2 < l3
            
            if shoulders_similar and head_lower:
                df.loc[i, "inv_head_and_shoulders"] = True
                shoulder_match = 1.0 - (abs(l1 - l3) / l1)
                head_depth = ((l1 + l3) / 2 - l2) / ((l1 + l3) / 2)
                df.loc[i, "inv_head_and_shoulders_conf"] = (
                    shoulder_match * 0.5 + min(head_depth / 0.15, 1.0) * 0.5
                ).clip(0, 1)
        
        # ----------------------
        # WEDGES
        # ----------------------
        if len(highs) >= 5 and len(lows) >= 5:
            h_vals = highs.tail(5)["swing_high"].values
            l_vals = lows.tail(5)["swing_low"].values
            x = np.arange(len(h_vals))
            
            high_slope = np.polyfit(x, h_vals, 1)[0]
            low_slope = np.polyfit(x, l_vals, 1)[0]
            
            # Rising Wedge (both rising, but lower converging faster)
            if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
                df.loc[i, "rising_wedge"] = True
                slope_diff = (low_slope - high_slope) / abs(high_slope)
                df.loc[i, "rising_wedge_conf"] = min(slope_diff / 0.5, 1.0)
            
            # Falling Wedge
            if high_slope < 0 and low_slope < 0 and low_slope < high_slope:
                df.loc[i, "falling_wedge"] = True
                slope_diff = (high_slope - low_slope) / abs(low_slope)
                df.loc[i, "falling_wedge_conf"] = min(slope_diff / 0.5, 1.0)
        
        # ----------------------
        # TRIANGLES
        # ----------------------
        if len(highs) >= 5 and len(lows) >= 5:
            h_vals = highs.tail(5)["swing_high"].values
            l_vals = lows.tail(5)["swing_low"].values
            x = np.arange(len(h_vals))
            
            high_slope = np.polyfit(x, h_vals, 1)[0]
            low_slope = np.polyfit(x, l_vals, 1)[0]
            high_trend = high_slope < 0
            low_trend = low_slope > 0
            
            # Symmetric Triangle (both converging)
            if high_trend and low_trend:
                df.loc[i, "sym_triangle"] = True
                convergence = (abs(high_slope) + abs(low_slope)) / ((h_vals[-1] - l_vals[-1]) + 1e-9)
                df.loc[i, "sym_triangle_conf"] = min(convergence / 0.1, 1.0)
            
            # Ascending Triangle (resistance flat, support rising)
            if abs(high_slope) < 0.001 and low_trend:
                df.loc[i, "asc_triangle"] = True
                resistance_flatness = 1.0 - abs(high_slope) * 10
                df.loc[i, "asc_triangle_conf"] = (resistance_flatness * 0.5 + 0.5)
            
            # Descending Triangle (support flat, resistance falling)
            if high_trend and abs(low_slope) < 0.001:
                df.loc[i, "desc_triangle"] = True
                support_flatness = 1.0 - abs(low_slope) * 10
                df.loc[i, "desc_triangle_conf"] = (support_flatness * 0.5 + 0.5)
        
        # ----------------------
        # RECTANGLE
        # ----------------------
        if len(highs) >= 5 and len(lows) >= 5:
            h_vals = highs.tail(5)["swing_high"].values
            l_vals = lows.tail(5)["swing_low"].values
            
            h_std = h_vals.std()
            l_std = l_vals.std()
            mid_price = df.loc[i, "close"]
            
            if h_std < 0.015 * mid_price and l_std < 0.015 * mid_price:
                df.loc[i, "rectangle"] = True
                flatness = 1.0 - (h_std + l_std) / (2 * 0.015 * mid_price)
                df.loc[i, "rectangle_conf"] = flatness
        
        # ----------------------
        # CHANNEL
        # ----------------------
        if len(highs) >= 5 and len(lows) >= 5:
            h_vals = highs.tail(5)["swing_high"].values
            l_vals = lows.tail(5)["swing_low"].values
            x = np.arange(len(h_vals))
            
            high_slope = np.polyfit(x, h_vals, 1)[0]
            low_slope = np.polyfit(x, l_vals, 1)[0]
            
            if abs(high_slope - low_slope) < 0.001:
                df.loc[i, "channel"] = True
                parallelism = 1.0 - abs(high_slope - low_slope) * 100
                df.loc[i, "channel_conf"] = parallelism.clip(0, 1)
        
        # ----------------------
        # FLAG
        # ----------------------
        recent = sub.tail(30)
        if len(recent) >= 30:
            move = recent["close"].iloc[-1] - recent["close"].iloc[0]
            volatility = recent["close"].std()
            recent_volatility = recent.tail(10)["high"].subtract(recent.tail(10)["low"]).mean()
            
            if abs(move) > volatility:
                if recent_volatility < volatility * 0.4:
                    df.loc[i, "flag"] = True
                    move_strength = abs(move) / volatility
                    consolidation_tightness = 1.0 - (recent_volatility / volatility)
                    df.loc[i, "flag_conf"] = (
                        move_strength.clip(0, 2) / 2 * 0.5 + consolidation_tightness * 0.5
                    ).clip(0, 1)
        
        # ----------------------
        # ROUNDING BOTTOM
        # ----------------------
        closes = sub["close"].tail(40).values
        if len(closes) >= 40:
            x = np.arange(len(closes))
            coeffs = np.polyfit(x, closes, 2)
            
            if coeffs[0] > 0:  # Parabolic curve upward
                df.loc[i, "rounding_bottom"] = True
                # Confidence based on curvature strength
                fit = np.polyval(coeffs, x)
                residual = np.mean(np.abs(closes - fit))
                curvature = coeffs[0]
                df.loc[i, "rounding_bottom_conf"] = (
                    min(curvature / 0.001, 1.0) * 0.6 +
                    (1.0 - residual / closes.std()) * 0.4
                ).clip(0, 1)
        
        # ----------------------
        # CUP & HANDLE
        # ----------------------
        closes = sub["close"].tail(50).values
        if len(closes) >= 50:
            mid = len(closes) // 2
            left = closes[:mid]
            right = closes[mid:]
            
            # Cup: left side down, right side up
            left_trend = np.polyfit(np.arange(len(left)), left, 1)[0] < 0
            right_trend = np.polyfit(np.arange(len(right)), right, 1)[0] > 0
            
            # Handle: right side should pullback slightly then continue up
            min_idx = np.argmin(closes)
            cup_exists = left_trend and right_trend and min_idx < len(closes) * 0.6
            
            if cup_exists:
                df.loc[i, "cup_handle"] = True
                cup_symmetry = 1.0 - abs((len(left) - (len(closes) - min_idx)) / len(closes))
                recovery = (closes[-1] - closes[min_idx]) / (np.max(left) - closes[min_idx] + 1e-9)
                df.loc[i, "cup_handle_conf"] = (
                    cup_symmetry * 0.4 + min(recovery, 1.0) * 0.6
                ).clip(0, 1)
    
    return df








def plot_with_annotations(df):
    df_plot = df.copy()

    df_plot = df_plot.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })

    df_plot.index = pd.to_datetime(df_plot.index)

    # Create numeric x positions
    x_vals = np.arange(len(df_plot))

    # Plot
    fig, axlist = mpf.plot(
        df_plot,
        type="candle",
        style="charles",
        returnfig=True,
        figsize=(14, 7)
    )

    ax = axlist[0]

    # --- Annotate ---
    for idx, (i, row) in enumerate(df.iterrows()):
        label = None
        color = "black"

        if row["hammer"]:
            label = "Hammer"
            color = "green"
        elif row["shooting_star"]:
            label = "ShootStar"
            color = "red"
        elif row["bullish_engulfing"]:
            label = "BullEng"
            color = "green"
        elif row["bearish_engulfing"]:
            label = "BearEng"
            color = "red"
        elif row["doji"]:
            label = "Doji"
            color = "blue"

        if label:
            ax.annotate(
                label,
                xy=(idx, row["high"]),
                xytext=(idx, row["high"] * 1.02),
                fontsize=8,
                color=color,
                ha="center",
                arrowprops=dict(
                    arrowstyle="->",
                    color=color,
                    lw=0.8
                )
            )

    return fig





def plot_valid_signals(df):
    df_plot = df.copy()

    df_plot = df_plot.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })

    df_plot.index = pd.to_datetime(df_plot.index)

    # Reduce clutter
    df_plot = df_plot.tail(120)
    df = df.tail(120).reset_index(drop=True)

    bullish_markers = np.full(len(df), np.nan)
    bearish_markers = np.full(len(df), np.nan)

    # Store annotation info
    annotations = []

    for i, row in df.iterrows():

        # 🟢 Bullish
        if row.get("hammer_valid", False):
            bullish_markers[i] = row["low"] * 0.995
            annotations.append((i, row["low"], "Hammer", "green"))

        elif row.get("bullish_engulfing_valid", False):
            bullish_markers[i] = row["low"] * 0.995
            annotations.append((i, row["low"], "BullEng", "green"))

        elif row.get("morning_star_valid", False):
            bullish_markers[i] = row["low"] * 0.995
            annotations.append((i, row["low"], "Morning*", "green"))

        elif row.get("piercing_line", False):
            bullish_markers[i] = row["low"] * 0.995
            annotations.append((i, row["low"], "Piercing", "green"))

        # 🔴 Bearish
        elif row.get("hanging_man_valid", False):
            bearish_markers[i] = row["high"] * 1.005
            annotations.append((i, row["high"], "HangMan", "red"))

        elif row.get("shooting_star_valid", False):
            bearish_markers[i] = row["high"] * 1.005
            annotations.append((i, row["high"], "Shoot*", "red"))

        elif row.get("bearish_engulfing_valid", False):
            bearish_markers[i] = row["high"] * 1.005
            annotations.append((i, row["high"], "BearEng", "red"))

        elif row.get("evening_star_valid", False):
            bearish_markers[i] = row["high"] * 1.005
            annotations.append((i, row["high"], "Evening*", "red"))

        elif row.get("dark_cloud_cover", False):
            bearish_markers[i] = row["high"] * 1.005
            annotations.append((i, row["high"], "DarkCloud", "red"))

    apds = []

    if not np.isnan(bullish_markers).all():
        apds.append(
            mpf.make_addplot(
                bullish_markers,
                type='scatter',
                marker='^',
                markersize=80
            )
        )

    if not np.isnan(bearish_markers).all():
        apds.append(
            mpf.make_addplot(
                bearish_markers,
                type='scatter',
                marker='v',
                markersize=80
            )
        )

    fig, axlist = mpf.plot(
        df_plot,
        type="candle",
        style="charles",
        addplot=apds,
        figsize=(14, 7),
        returnfig=True
    )

    ax = axlist[0]

    # --- Add text annotations ---
    y_offset = (df["high"].max() - df["low"].min()) * 0.02

    for x, y, text, color in annotations:
        if color == "green":
            y_text = y - y_offset
        else:
            y_text = y + y_offset

        ax.text(
            x,
            y_text,
            text,
            color=color,
            fontsize=8,
            ha="center",
            va="center"
        )

    return fig





def plot_chart_patterns(df):
    # --- Prepare data ---
    df_plot = df.copy()

    df_plot = df_plot.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })

    df_plot.index = pd.to_datetime(df_plot.index)

    # Focus on recent data (important for clarity)
    df_plot = df_plot.tail(120)
    df = df.tail(120).reset_index(drop=True)

    # --- Plot base chart ---
    fig, axlist = mpf.plot(
        df_plot,
        type="candle",
        style="charles",
        figsize=(14, 7),
        returnfig=True
    )

    ax = axlist[0]

    # =========================
    # 🧠 Pattern Detection (RECENT WINDOW)
    # =========================

    recent = df.tail(5)   # last few candles (important)

    def detected(col):
        return col in df.columns and recent[col].any()

    # =========================
    # 📍 Positioning
    # =========================

    x = len(df) - 10  # shift labels left
    y_high = df["high"].max()
    y_low = df["low"].min()
    y_mid = df["close"].iloc[-1]

    y_range = y_high - y_low
    y_offset = y_range * 0.06

    labels = []

    # =========================
    # 🔻 REVERSAL PATTERNS
    # =========================

    if detected("double_top"):
        labels.append(("Double Top", y_high))

    if detected("double_bottom"):
        labels.append(("Double Bottom", y_low))

    if detected("head_and_shoulders"):
        labels.append(("H&S", y_high))

    if detected("inv_head_and_shoulders"):
        labels.append(("Inv H&S", y_low))

    if detected("rounding_bottom"):
        labels.append(("Rounding Bottom", y_low))

    if detected("rising_wedge"):
        labels.append(("Rising Wedge", y_high))

    if detected("falling_wedge"):
        labels.append(("Falling Wedge", y_low))

    # =========================
    # 🔁 CONTINUATION PATTERNS
    # =========================

    if detected("sym_triangle"):
        labels.append(("Sym Triangle", y_mid))

    if detected("asc_triangle"):
        labels.append(("Asc Triangle", y_mid))

    if detected("flag"):
        labels.append(("Flag", y_mid))

    if detected("rectangle"):
        labels.append(("Rectangle", y_mid))

    if detected("channel"):
        labels.append(("Channel", y_mid))

    if detected("cup_handle"):
        labels.append(("Cup&Handle", y_mid))

    # =========================
    # 🖊️ DRAW LABELS
    # =========================

    for i, (text, y) in enumerate(labels):
        ax.text(
            x,
            y + (i * y_offset * 0.6),
            text,
            fontsize=9,
            ha="left",
            bbox=dict(
                facecolor="white",
                alpha=0.7,
                edgecolor="black"
            )
        )

    return fig


# --- Usage ---
# if __name__ == "__main__":
#     df = pd.read_csv("data.csv")

#     # IMPORTANT: index must be datetime or numeric index
#     df.index = pd.to_datetime(df["date"])

#     df = detect_candles(df)

#     fig = plot_with_annotations(df)