import numpy as np
import pandas as pd
import mplfinance as mpf
from scipy import signal


def detect_support_resistance_claude(df, window=5, tolerance=0.01, min_touches=2):
    """
    Improved support/resistance detection with:
    - Relative extrema detection (scipy.signal)
    - K-means style clustering with convergence
    - Confidence scores based on touch count and clustering tightness
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        window: Lookback window for swing detection
        tolerance: Relative price tolerance for clustering (0.01 = 1%)
        min_touches: Minimum touches required for a level
    
    Returns:
        support: [(level, strength, confidence), ...] sorted by confidence
        resistance: [(level, strength, confidence), ...] sorted by confidence
        df: DataFrame with added columns including confidence scores and zone counts
    """
    df = df.copy()
    
    # =========================
    # 1. Swing Points Detection
    # =========================
    # Use scipy.signal.argrelextrema to find local maxima/minima
    # More robust than exact rolling max/min which is too strict
    
    high_indices = signal.argrelextrema(df["high"].values, np.greater_equal, order=window)[0]
    low_indices = signal.argrelextrema(df["low"].values, np.less_equal, order=window)[0]
    
    swing_highs = df.iloc[high_indices]["high"].values
    swing_lows = df.iloc[low_indices]["low"].values

    # Filter noise: remove swings that are outliers (1 std below/above mean)
    if len(swing_highs) > 0:
        high_mean = np.mean(swing_highs)
        high_std = np.std(swing_highs)
        swing_highs = swing_highs[swing_highs > (high_mean - high_std)]
    
    if len(swing_lows) > 0:
        low_mean = np.mean(swing_lows)
        low_std = np.std(swing_lows)
        swing_lows = swing_lows[swing_lows < (low_mean + low_std)]
    
    # =========================
    # 2. Robust Clustering
    # =========================
    def cluster_levels(levels, tolerance, max_iterations=10):
        """
        Cluster price levels using iterative merging.
        Avoids order-dependency of naive sequential clustering.
        """
        if len(levels) == 0:
            return []
        
        # Start with each level as its own cluster
        clusters = [{"values": [lvl], "mean": lvl} for lvl in levels]
        
        # Iteratively merge nearby clusters
        for iteration in range(max_iterations):
            merged = False
            clusters = sorted(clusters, key=lambda x: x["mean"])
            
            i = 0
            while i < len(clusters) - 1:
                c1 = clusters[i]
                c2 = clusters[i + 1]
                
                # Merge if means are within tolerance
                if abs(c1["mean"] - c2["mean"]) / c1["mean"] < tolerance:
                    c1["values"].extend(c2["values"])
                    c1["mean"] = np.mean(c1["values"])
                    clusters.pop(i + 1)
                    merged = True
                else:
                    i += 1
            
            if not merged:
                break
        
        return clusters
    
    high_clusters = cluster_levels(swing_highs, tolerance)
    low_clusters = cluster_levels(swing_lows, tolerance)
    
    # =========================
    # 3. Build Levels with Confidence Scoring
    # =========================
    def build_levels(clusters, min_touches):
        """
        Convert clusters to (level, strength, confidence) tuples.
        
        Confidence combines:
        - Touch count: more touches = higher confidence (saturates at 5)
        - Clustering tightness: tighter cluster = higher confidence
        """
        levels = []
        
        for c in clusters:
            if len(c["values"]) >= min_touches:
                mean = c["mean"]
                strength = len(c["values"])
                
                # Component 1: Touch count factor (0-1, saturate at 5 touches)
                touch_factor = min(strength / 5.0, 1.0)
                
                # Component 2: Clustering tightness
                # Lower std relative to mean = tighter cluster = higher confidence
                std_dev = np.std(c["values"])
                tightness = 1.0 - (std_dev / mean) if mean > 0 else 1.0
                tightness = max(0.0, min(tightness, 1.0))
                
                # Weighted average: 60% touches, 40% tightness
                confidence = 0.6 * touch_factor + 0.4 * tightness
                
                levels.append((mean, strength, confidence))
        
        # Sort by confidence (highest first)
        return sorted(levels, key=lambda x: -x[2])
    
    resistance = build_levels(high_clusters, min_touches)
    support = build_levels(low_clusters, min_touches)
    
    # =========================
    # 4. Add Features to DataFrame
    # =========================
    df["near_support"] = False
    df["near_resistance"] = False
    
    df["dist_to_support"] = np.nan
    df["dist_to_resistance"] = np.nan
    
    df["support_strength"] = 0  # Touch count
    df["resistance_strength"] = 0
    
    df["support_confidence"] = 0.0  # Confidence score
    df["resistance_confidence"] = 0.0
    
    df["support_zone_count"] = 0  # How many support levels nearby
    df["resistance_zone_count"] = 0
    
    for i, row in df.iterrows():
        price = row["close"]
        
        # ---- Support ----
        if support:
            dists = [(abs(price - lvl[0]), lvl) for lvl in support]
            best = min(dists, key=lambda x: x[0])[1]
            
            dist_ratio = abs(price - best[0]) / best[0]
            
            df.at[i, "dist_to_support"] = dist_ratio
            df.at[i, "support_strength"] = best[1]
            df.at[i, "support_confidence"] = best[2]
            
            # Count nearby support levels (zone detection)
            nearby = sum(1 for lvl in support 
                        if abs(price - lvl[0]) / best[0] < tolerance * 2)
            df.at[i, "support_zone_count"] = nearby
            
            if dist_ratio < tolerance:
                df.at[i, "near_support"] = True
        
        # ---- Resistance ----
        if resistance:
            dists = [(abs(price - lvl[0]), lvl) for lvl in resistance]
            best = min(dists, key=lambda x: x[0])[1]
            
            dist_ratio = abs(price - best[0]) / best[0]
            
            df.at[i, "dist_to_resistance"] = dist_ratio
            df.at[i, "resistance_strength"] = best[1]
            df.at[i, "resistance_confidence"] = best[2]
            
            # Count nearby resistance levels
            nearby = sum(1 for lvl in resistance 
                        if abs(price - lvl[0]) / best[0] < tolerance * 2)
            df.at[i, "resistance_zone_count"] = nearby
            
            if dist_ratio < tolerance:
                df.at[i, "near_resistance"] = True
    
    return support, resistance, df





def detect_support_resistance(df, window=5, tolerance=0.01, min_touches=2):
    df = df.copy()

    # =========================
    # 1. Swing Points
    # =========================
    df["swing_high"] = df["high"][
        (df["high"] == df["high"].rolling(window, center=True).max())
    ]

    df["swing_low"] = df["low"][
        (df["low"] == df["low"].rolling(window, center=True).min())
    ]

    swing_highs = df["swing_high"].dropna().values
    swing_lows = df["swing_low"].dropna().values

    # =========================
    # 2. Clustering
    # =========================
    def cluster(levels):
        clusters = []

        for level in levels:
            assigned = False
            for c in clusters:
                if abs(level - c["mean"]) / c["mean"] < tolerance:
                    c["values"].append(level)
                    c["mean"] = np.mean(c["values"])
                    assigned = True
                    break

            if not assigned:
                clusters.append({"values": [level], "mean": level})

        return clusters

    high_clusters = cluster(swing_highs)
    low_clusters = cluster(swing_lows)

    # =========================
    # 3. Filter by strength
    # =========================
    resistance = [(c["mean"], len(c["values"])) for c in high_clusters if len(c["values"]) >= min_touches]
    support = [(c["mean"], len(c["values"])) for c in low_clusters if len(c["values"]) >= min_touches]

    resistance = sorted(resistance, key=lambda x: -x[1])
    support = sorted(support, key=lambda x: -x[1])

    # =========================
    # 4. Add Features to df
    # =========================

    df["near_support"] = False
    df["near_resistance"] = False

    df["dist_to_support"] = np.nan
    df["dist_to_resistance"] = np.nan

    df["support_strength"] = 0
    df["resistance_strength"] = 0

    for i, row in df.iterrows():
        price = row["close"]

        # ---- Support ----
        if support:
            dists = [(abs(price - lvl[0]), lvl) for lvl in support]
            best = min(dists, key=lambda x: x[0])[1]

            dist = abs(price - best[0]) / best[0]

            df.at[i, "dist_to_support"] = dist
            df.at[i, "support_strength"] = best[1]

            if dist < tolerance:
                df.at[i, "near_support"] = True

        # ---- Resistance ----
        if resistance:
            dists = [(abs(price - lvl[0]), lvl) for lvl in resistance]
            best = min(dists, key=lambda x: x[0])[1]

            dist = abs(price - best[0]) / best[0]

            df.at[i, "dist_to_resistance"] = dist
            df.at[i, "resistance_strength"] = best[1]

            if dist < tolerance:
                df.at[i, "near_resistance"] = True

    return support, resistance, df




def plot_support_resistance(df, support, resistance, top_n=3):
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
    df_plot.index = pd.to_datetime(df_plot.index)

    # Select strongest levels
    support = sorted(support, key=lambda x: -x[1])[:top_n]
    resistance = sorted(resistance, key=lambda x: -x[1])[:top_n]

    fig, axlist = mpf.plot(
        df_plot,
        type="candle",
        style="charles",
        figsize=(14, 7),
        datetime_format="%Y-%m-%d",
        xrotation=45,
        returnfig=True
    )

    ax = axlist[0]

    price_range = df["high"].max() - df["low"].min()
    zone_width = price_range * 0.01  # zone thickness

    x_end = len(df) - 1
    x_start = x_end - 80

    # =========================
    # 🟢 SUPPORT ZONES
    # =========================
    for price, strength, confidence in support:
        lower = price - zone_width
        upper = price + zone_width

        ax.fill_between(
            [x_start, x_end],
            lower,
            upper,
            alpha=0.2,
            color="green"
        )

        ax.text(
            x_start,
            price,
            f"S ({strength} | {confidence*100:.0f}%)",
            color="green",
            fontsize=9,
            va="center"
        )

    # =========================
    # 🔴 RESISTANCE ZONES
    # =========================
    for price, strength, confidence in resistance:
        lower = price - zone_width
        upper = price + zone_width

        ax.fill_between(
            [x_start, x_end],
            lower,
            upper,
            alpha=0.2,
            color="red"
        )

        ax.text(
            x_start,
            price,
            f"S ({strength} | {confidence*100:.0f}%)",
            color="red",
            fontsize=9,
            va="center"
        )

    return fig





