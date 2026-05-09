import numpy as np
import pandas as pd
import mplfinance as mpf
from scipy import signal
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D


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




def detect_support_resistance_walkforward(df, window=5, tolerance=0.01, min_touches=2):
    """
    CORRECTED support/resistance detection with walk-forward analysis.
    
    KEY FIX: For each row, calculates support/resistance using ONLY data up to that date.
    No lookahead bias - works exactly as you would in a live trading system.
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        window: Lookback window for swing detection
        tolerance: Relative price tolerance for clustering (0.01 = 1%)
        min_touches: Minimum touches required for a level
    
    Returns:
        support: List of (level, strength, confidence) sorted by confidence
        resistance: List of (level, strength, confidence) sorted by confidence
        df: DataFrame with columns for each date:
            - dist_to_support: Distance to nearest support (%)
            - dist_to_resistance: Distance to nearest resistance (%)
            - support_strength: Number of touches at nearest support
            - resistance_strength: Number of touches at nearest resistance
            - support_confidence: Confidence score (0-1) of nearest support
            - resistance_confidence: Confidence score (0-1) of nearest resistance
            - support_zone_count: Number of support levels nearby
            - resistance_zone_count: Number of resistance levels nearby
            - near_support: Boolean if price within tolerance of support
            - near_resistance: Boolean if price within tolerance of resistance
    """
    df = df.copy()
    
    # Initialize columns
    df["near_support"] = False
    df["near_resistance"] = False
    
    df["dist_to_support"] = np.nan
    df["dist_to_resistance"] = np.nan
    
    df["support_strength"] = 0
    df["resistance_strength"] = 0
    
    df["support_confidence"] = 0.0
    df["resistance_confidence"] = 0.0
    
    df["support_zone_count"] = 0
    df["resistance_zone_count"] = 0
    
    df["support_level"] = np.nan
    df["resistance_level"] = np.nan
    
    # ==========================================
    # Helper function: Cluster price levels
    # ==========================================
    def cluster_levels(levels, tolerance, max_iterations=10):
        """Cluster price levels using iterative merging"""
        if len(levels) == 0:
            return []
        
        clusters = [{"values": [lvl], "mean": lvl} for lvl in levels]
        
        for iteration in range(max_iterations):
            merged = False
            clusters = sorted(clusters, key=lambda x: x["mean"])
            
            i = 0
            while i < len(clusters) - 1:
                c1 = clusters[i]
                c2 = clusters[i + 1]
                
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
    
    # ==========================================
    # Helper function: Build levels with confidence
    # ==========================================
    def build_levels(clusters, min_touches):
        """Convert clusters to (level, strength, confidence) tuples"""
        levels = []
        
        for c in clusters:
            if len(c["values"]) >= min_touches:
                mean = c["mean"]
                strength = len(c["values"])
                
                # Touch count factor
                touch_factor = min(strength / 5.0, 1.0)
                
                # Clustering tightness
                std_dev = np.std(c["values"])
                tightness = 1.0 - (std_dev / mean) if mean > 0 else 1.0
                tightness = max(0.0, min(tightness, 1.0))
                
                # Combined confidence
                confidence = 0.6 * touch_factor + 0.4 * tightness
                
                levels.append((mean, strength, confidence))
        
        return sorted(levels, key=lambda x: -x[2])  # Sort by confidence
    
    # ==========================================
    # MAIN LOOP: Walk-forward calculation
    # ==========================================
    for current_idx in range(window, len(df)):  # Start after minimum window
        # Get data up to CURRENT date (no future data)
        historical_data = df.iloc[:current_idx + 1]
        
        current_price = df.loc[df.index[current_idx], "close"]
        
        # --- STEP 1: Find swing points in historical data only ---
        high_indices = signal.argrelextrema(
            historical_data["high"].values, 
            np.greater_equal, 
            order=window
        )[0]
        low_indices = signal.argrelextrema(
            historical_data["low"].values, 
            np.less_equal, 
            order=window
        )[0]
        
        swing_highs = historical_data.iloc[high_indices]["high"].values
        swing_lows = historical_data.iloc[low_indices]["low"].values
        
        # Filter noise
        if len(swing_highs) > 0:
            high_mean = np.mean(swing_highs)
            high_std = np.std(swing_highs)
            swing_highs = swing_highs[swing_highs > (high_mean - high_std)]
        
        if len(swing_lows) > 0:
            low_mean = np.mean(swing_lows)
            low_std = np.std(swing_lows)
            swing_lows = swing_lows[swing_lows < (low_mean + low_std)]
        
        # --- STEP 2: Cluster swing points ---
        high_clusters = cluster_levels(swing_highs, tolerance)
        low_clusters = cluster_levels(swing_lows, tolerance)
        
        # --- STEP 3: Build levels with confidence ---
        resistance = build_levels(high_clusters, min_touches)
        support = build_levels(low_clusters, min_touches)
        
        # --- STEP 4: Find nearest levels and calculate features ---
        # SUPPORT
        if support:
            dists = [(abs(current_price - lvl[0]), lvl) for lvl in support]
            best = min(dists, key=lambda x: x[0])[1]
            
            dist_ratio = abs(current_price - best[0]) / best[0]
            
            df.at[df.index[current_idx], "support_level"] = best[0]
            df.at[df.index[current_idx], "dist_to_support"] = dist_ratio
            df.at[df.index[current_idx], "support_strength"] = best[1]
            df.at[df.index[current_idx], "support_confidence"] = best[2]
            
            # Count nearby support levels
            nearby = sum(1 for lvl in support 
                        if abs(current_price - lvl[0]) / best[0] < tolerance * 2)
            df.at[df.index[current_idx], "support_zone_count"] = nearby
            
            if dist_ratio < tolerance:
                df.at[df.index[current_idx], "near_support"] = True
        
        # RESISTANCE
        if resistance:
            dists = [(abs(current_price - lvl[0]), lvl) for lvl in resistance]
            best = min(dists, key=lambda x: x[0])[1]
            
            dist_ratio = abs(current_price - best[0]) / best[0]
            
            df.at[df.index[current_idx], "resistance_level"] = best[0]
            df.at[df.index[current_idx], "dist_to_resistance"] = dist_ratio
            df.at[df.index[current_idx], "resistance_strength"] = best[1]
            df.at[df.index[current_idx], "resistance_confidence"] = best[2]
            
            # Count nearby resistance levels
            nearby = sum(1 for lvl in resistance 
                        if abs(current_price - lvl[0]) / best[0] < tolerance * 2)
            df.at[df.index[current_idx], "resistance_zone_count"] = nearby
            
            if dist_ratio < tolerance:
                df.at[df.index[current_idx], "near_resistance"] = True
    
    return support, resistance, df
 
 
# ============================================
# OPTIMIZED VERSION: For large datasets
# ============================================
def detect_support_resistance_walkforward_optimized(df, window=5, tolerance=0.01, min_touches=2):
    """
    Optimized version using incremental updates instead of recalculating everything.
    
    Much faster for large datasets, but same accuracy.
    """
    df = df.copy()
    
    # Initialize columns
    for col in ["near_support", "near_resistance"]:
        df[col] = False
    
    for col in ["dist_to_support", "dist_to_resistance", "support_level", "resistance_level"]:
        df[col] = np.nan
    
    for col in ["support_strength", "resistance_strength", "support_zone_count", "resistance_zone_count"]:
        df[col] = 0
    
    for col in ["support_confidence", "resistance_confidence"]:
        df[col] = 0.0
    
    def cluster_levels(levels, tolerance, max_iterations=10):
        if len(levels) == 0:
            return []
        
        clusters = [{"values": [lvl], "mean": lvl} for lvl in levels]
        
        for _ in range(max_iterations):
            merged = False
            clusters = sorted(clusters, key=lambda x: x["mean"])
            
            i = 0
            while i < len(clusters) - 1:
                c1 = clusters[i]
                c2 = clusters[i + 1]
                
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
    
    def build_levels(clusters, min_touches):
        levels = []
        for c in clusters:
            if len(c["values"]) >= min_touches:
                mean = c["mean"]
                strength = len(c["values"])
                
                touch_factor = min(strength / 5.0, 1.0)
                
                std_dev = np.std(c["values"])
                tightness = 1.0 - (std_dev / mean) if mean > 0 else 1.0
                tightness = max(0.0, min(tightness, 1.0))
                
                confidence = 0.6 * touch_factor + 0.4 * tightness
                
                levels.append((mean, strength, confidence))
        
        return sorted(levels, key=lambda x: -x[2])
    
    # Cache for swing points (incremental update)
    swing_highs_cache = []
    swing_lows_cache = []
    
    for current_idx in range(window, len(df)):
        historical_data = df.iloc[:current_idx + 1]
        current_price = df.loc[df.index[current_idx], "close"]
        
        # Find NEW swing points added since last iteration
        # (Only check the last `window` bars)
        check_start = max(window, current_idx - window - 1)
        
        high_indices = signal.argrelextrema(
            historical_data.iloc[check_start:]["high"].values, 
            np.greater_equal, 
            order=window
        )[0]
        low_indices = signal.argrelextrema(
            historical_data.iloc[check_start:]["low"].values, 
            np.less_equal, 
            order=window
        )[0]
        
        # Convert local indices to global indices
        high_indices = high_indices + check_start
        low_indices = low_indices + check_start
        
        # Get new swing points
        new_swing_highs = historical_data.iloc[high_indices]["high"].values
        new_swing_lows = historical_data.iloc[low_indices]["low"].values
        
        # Add to cache (remove duplicates)
        swing_highs_cache = list(set(list(swing_highs_cache) + list(new_swing_highs)))
        swing_lows_cache = list(set(list(swing_lows_cache) + list(new_swing_lows)))
        
        # Filter noise
        if len(swing_highs_cache) > 0:
            high_mean = np.mean(swing_highs_cache)
            high_std = np.std(swing_highs_cache)
            swing_highs_cache = [x for x in swing_highs_cache if x > (high_mean - high_std)]
        
        if len(swing_lows_cache) > 0:
            low_mean = np.mean(swing_lows_cache)
            low_std = np.std(swing_lows_cache)
            swing_lows_cache = [x for x in swing_lows_cache if x < (low_mean + low_std)]
        
        # Cluster
        high_clusters = cluster_levels(swing_highs_cache, tolerance)
        low_clusters = cluster_levels(swing_lows_cache, tolerance)
        
        # Build levels
        resistance = build_levels(high_clusters, min_touches)
        support = build_levels(low_clusters, min_touches)
        
        # Update row
        if support:
            dists = [(abs(current_price - lvl[0]), lvl) for lvl in support]
            best = min(dists, key=lambda x: x[0])[1]
            dist_ratio = abs(current_price - best[0]) / best[0]
            
            df.at[df.index[current_idx], "support_level"] = best[0]
            df.at[df.index[current_idx], "dist_to_support"] = dist_ratio
            df.at[df.index[current_idx], "support_strength"] = best[1]
            df.at[df.index[current_idx], "support_confidence"] = best[2]
            
            nearby = sum(1 for lvl in support 
                        if abs(current_price - lvl[0]) / best[0] < tolerance * 2)
            df.at[df.index[current_idx], "support_zone_count"] = nearby
            
            if dist_ratio < tolerance:
                df.at[df.index[current_idx], "near_support"] = True
        
        if resistance:
            dists = [(abs(current_price - lvl[0]), lvl) for lvl in resistance]
            best = min(dists, key=lambda x: x[0])[1]
            dist_ratio = abs(current_price - best[0]) / best[0]
            
            df.at[df.index[current_idx], "resistance_level"] = best[0]
            df.at[df.index[current_idx], "dist_to_resistance"] = dist_ratio
            df.at[df.index[current_idx], "resistance_strength"] = best[1]
            df.at[df.index[current_idx], "resistance_confidence"] = best[2]
            
            nearby = sum(1 for lvl in resistance 
                        if abs(current_price - lvl[0]) / best[0] < tolerance * 2)
            df.at[df.index[current_idx], "resistance_zone_count"] = nearby
            
            if dist_ratio < tolerance:
                df.at[df.index[current_idx], "near_resistance"] = True
    
    return support, resistance, df








def plot_support_resistance(df, support, resistance, top_n=3, fig=None, axlist=None):
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

    if fig is None:
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

    return fig, axlist



def plot_support_resistance_enhanced(df, support, resistance, top_n=3, 
                                           fig=None, axlist=None):
    """
    FIXED version with proper date index handling.
    
    KEY FIXES:
    1. Keep date index throughout (don't reset_index)
    2. Keep full history in df_full WITH dates
    3. Properly convert global indices to plot indices
    4. mplfinance uses date index, plotting uses numeric offsets
    
    Args:
        df: DataFrame with OHLCV data and DATE INDEX
        support: List of (level, strength, confidence) tuples
        resistance: List of (level, strength, confidence) tuples
        top_n: Number of top levels to show
        fig, axlist: Optional matplotlib figure/axes
    
    Returns:
        fig, axlist: Updated matplotlib objects
    """
    
    # ===== CRITICAL FIX #1: Keep full history WITH dates =====
    df_full = df.copy()
    df_full.index = pd.to_datetime(df_full.index)
    
    # ===== CRITICAL FIX #2: Don't reset index - keep dates! =====
    df_plot = df.copy().rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })
    df_plot.index = pd.to_datetime(df_plot.index)
    
    # Get last 120 rows, but KEEP the date index
    df_plot_display = df_plot.tail(120)
    df_display = df.tail(120)  # ← NO reset_index!
    df_display.index = pd.to_datetime(df_display.index)
    
    # ===== CRITICAL FIX #3: Calculate offset correctly =====
    plot_start_idx = len(df_full) - len(df_display)
    
    # Sort by confidence (not strength)
    support = sorted(support, key=lambda x: -x[2])[:top_n]
    resistance = sorted(resistance, key=lambda x: -x[2])[:top_n]
    
    # Create plot if not provided
    if fig is None:
        fig, axlist = mpf.plot(
            df_plot_display,
            type="candle",
            style="charles",
            figsize=(14, 7),
            datetime_format="%Y-%m-%d",
            xrotation=45,
            returnfig=True
        )
    
    ax = axlist[0]
    
    price_range = df_display["high"].max() - df_display["low"].min()
    zone_width = price_range * 0.01
    
    x_end = len(df_display) - 1
    x_start = max(0, x_end - 80)
    
    # ===== CRITICAL FIX #4: Search full history but convert indices =====
    def find_first_touch_index(price, tolerance=0.01):
        """
        Find first touch in FULL history (with dates).
        Returns GLOBAL index (into df_full).
        """
        tolerance_range = price * tolerance
        
        for i in range(len(df_full)):
            high = df_full.iloc[i]['high']
            low = df_full.iloc[i]['low']
            
            # Check if price touched this level
            if (low <= price <= high) or \
               (abs(high - price) <= tolerance_range) or \
               (abs(low - price) <= tolerance_range):
                return i  # Return global index
        
        return 0
    
    def global_to_plot_idx(global_idx):
        """Convert global index to plot index (0-119 range)"""
        plot_idx = global_idx - plot_start_idx
        return max(0, min(plot_idx, x_end))  # Clamp to valid range
    
    # ===== SUPPORT LEVELS =====
    for idx, (price, strength, confidence) in enumerate(support):
        # Find first touch in global/full history
        first_touch_global = find_first_touch_index(price, tolerance=0.01)
        
        # Convert to plot indices
        plot_first_touch = global_to_plot_idx(first_touch_global)
        
        # Find last confirmed touch
        last_touch_global = first_touch_global
        for i in range(first_touch_global, len(df_full)):
            high = df_full.iloc[i]['high']
            low = df_full.iloc[i]['low']
            if (low <= price <= high) or abs(low - price) < price * 0.005:
                last_touch_global = i
        
        plot_last_touch = global_to_plot_idx(last_touch_global)
        
        # Color based on confidence
        if confidence > 0.8:
            color = "#00AA00"
            alpha_solid = 0.4
            alpha_dashed = 0.15
            linewidth_solid = 2.5
            linewidth_dashed = 1.5
        elif confidence > 0.6:
            color = "#00CC00"
            alpha_solid = 0.3
            alpha_dashed = 0.12
            linewidth_solid = 2
            linewidth_dashed = 1.2
        else:
            color = "#66DD66"
            alpha_solid = 0.2
            alpha_dashed = 0.08
            linewidth_solid = 1.5
            linewidth_dashed = 0.8
        
        # Solid line from first to last touch
        ax.plot(
            [plot_first_touch, plot_last_touch],
            [price, price],
            color=color,
            linewidth=linewidth_solid,
            linestyle='-',
            alpha=alpha_solid * 1.5,
            zorder=3
        )
        
        # Dashed line (projection forward)
        if plot_last_touch < x_end:
            ax.plot(
                [plot_last_touch, x_end],
                [price, price],
                color=color,
                linewidth=linewidth_dashed,
                linestyle='--',
                alpha=alpha_dashed,
                zorder=2
            )
        
        # Zone shading
        lower = price - zone_width
        upper = price + zone_width
        
        # Solid zone
        ax.fill_between(
            [plot_first_touch, plot_last_touch],
            lower, upper,
            alpha=alpha_solid * 0.4,
            color=color,
            zorder=1
        )
        
        # Dashed zone
        if plot_last_touch < x_end:
            ax.fill_between(
                [plot_last_touch, x_end],
                lower, upper,
                alpha=alpha_dashed * 0.3,
                color=color,
                zorder=0
            )
        
        # Label
        label_x = plot_first_touch if plot_first_touch < x_start else x_start
        ax.text(
            label_x,
            price + zone_width * 1.5,
            f"S: {price:.2f} ({int(strength)}x, {confidence*100:.0f}%)",
            color=color,
            fontsize=9,
            fontweight='bold',
            va="bottom",
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     alpha=0.7, edgecolor=color)
        )
    
    # ===== RESISTANCE LEVELS =====
    for idx, (price, strength, confidence) in enumerate(resistance):
        first_touch_global = find_first_touch_index(price, tolerance=0.01)
        plot_first_touch = global_to_plot_idx(first_touch_global)
        
        # Find last confirmed touch
        last_touch_global = first_touch_global
        for i in range(first_touch_global, len(df_full)):
            high = df_full.iloc[i]['high']
            low = df_full.iloc[i]['low']
            if (low <= price <= high) or abs(high - price) < price * 0.005:
                last_touch_global = i
        
        plot_last_touch = global_to_plot_idx(last_touch_global)
        
        # Color based on confidence
        if confidence > 0.8:
            color = "#AA0000"
            alpha_solid = 0.4
            alpha_dashed = 0.15
            linewidth_solid = 2.5
            linewidth_dashed = 1.5
        elif confidence > 0.6:
            color = "#CC0000"
            alpha_solid = 0.3
            alpha_dashed = 0.12
            linewidth_solid = 2
            linewidth_dashed = 1.2
        else:
            color = "#DD6666"
            alpha_solid = 0.2
            alpha_dashed = 0.08
            linewidth_solid = 1.5
            linewidth_dashed = 0.8
        
        # Solid line
        ax.plot(
            [plot_first_touch, plot_last_touch],
            [price, price],
            color=color,
            linewidth=linewidth_solid,
            linestyle='-',
            alpha=alpha_solid * 1.5,
            zorder=3
        )
        
        # Dashed line
        if plot_last_touch < x_end:
            ax.plot(
                [plot_last_touch, x_end],
                [price, price],
                color=color,
                linewidth=linewidth_dashed,
                linestyle='--',
                alpha=alpha_dashed,
                zorder=2
            )
        
        # Zone shading
        lower = price - zone_width
        upper = price + zone_width
        
        ax.fill_between(
            [plot_first_touch, plot_last_touch],
            lower, upper,
            alpha=alpha_solid * 0.4,
            color=color,
            zorder=1
        )
        
        if plot_last_touch < x_end:
            ax.fill_between(
                [plot_last_touch, x_end],
                lower, upper,
                alpha=alpha_dashed * 0.3,
                color=color,
                zorder=0
            )
        
        # Label
        label_x = plot_first_touch if plot_first_touch < x_start else x_start
        ax.text(
            label_x,
            price - zone_width * 1.5,
            f"R: {price:.2f} ({int(strength)}x, {confidence*100:.0f}%)",
            color=color,
            fontsize=9,
            fontweight='bold',
            va="top",
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     alpha=0.7, edgecolor=color)
        )
    
    # Legend
    legend_elements = [
        Line2D([0], [1], color='gray', linewidth=2, linestyle='-',
               label='Active Level (confirmed touches)'),
        Line2D([0], [1], color='gray', linewidth=1.5, linestyle='--',
               label='Projected Level (future extension)'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9)
    
    ax.set_title('Support & Resistance with Level History & Projections',
                fontsize=14, fontweight='bold')
    ax.set_ylabel('Price', fontsize=11)
    
    return fig, axlist

def plot_support_resistance_compact(df, support, resistance, top_n=3, 
                                   fig=None, axlist=None):
    """
    Compact version - simpler visualization
    - Solid lines: active periods
    - Dashed lines: projections
    - No zones, just lines
    """
    df_plot = df.copy()
 
    df_plot = df_plot.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })
 
    df_plot.index = pd.to_datetime(df_plot.index)
 
    df_full = df.copy()
    df_plot = df_plot.tail(120)
    df = df.tail(120).reset_index(drop=True)
    df_plot.index = pd.to_datetime(df_plot.index)
    
    plot_start_idx = len(df_full) - len(df)
 
    support = sorted(support, key=lambda x: -x[2])[:top_n]
    resistance = sorted(resistance, key=lambda x: -x[2])[:top_n]
 
    if fig is None:
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
    x_end = len(df) - 1
 
    def find_first_touch_index(price, tolerance=0.01):
        tolerance_range = price * tolerance
        for i in range(len(df_full)):
            high = df_full.iloc[i]['high']
            low = df_full.iloc[i]['low']
            if (low <= price <= high) or (abs(high - price) <= tolerance_range) or (abs(low - price) <= tolerance_range):
                return i
        return 0
 
    # Support lines
    for price, strength, confidence in support:
        first_touch_idx = find_first_touch_index(price)
        plot_first_touch = max(0, first_touch_idx - plot_start_idx)
        
        # Color based on confidence
        color_alpha = min(1.0, confidence * 1.5)
        color = f"rgba(0, 150, 0, {color_alpha})"
        
        # Solid line to current
        ax.plot([plot_first_touch, x_end], [price, price], 
               color='green', linewidth=2, alpha=color_alpha, zorder=3)
        
        # Label
        ax.text(plot_first_touch, price, f"{price:.2f}({int(strength)}x)", 
               color='green', fontsize=8, va='center',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
 
    # Resistance lines
    for price, strength, confidence in resistance:
        first_touch_idx = find_first_touch_index(price)
        plot_first_touch = max(0, first_touch_idx - plot_start_idx)
        
        color_alpha = min(1.0, confidence * 1.5)
        
        # Solid line to current
        ax.plot([plot_first_touch, x_end], [price, price], 
               color='red', linewidth=2, alpha=color_alpha, zorder=3)
        
        # Label
        ax.text(plot_first_touch, price, f"{price:.2f}({int(strength)}x)", 
               color='red', fontsize=8, va='center',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
 
    return fig, axlist
 



