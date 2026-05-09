import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import warnings

warnings.filterwarnings("ignore")

import os
import sys
from pathlib import Path
import logging

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('screener_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)




PRICES_DIR = "database/historical_data_yf"


def load_data(stock_code="TCS"):
    file_path = f"{PRICES_DIR}/{stock_code}.NS_yf.json"
    df = pd.read_json(file_path).T
    
    dates = pd.to_datetime(df.index.tolist()).tolist()
    
    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock_code}.NS", '').lower() for c in cols]
    df.columns = cols
    return df, dates, cols


# =========================
# DATA STRUCTURES
# =========================

@dataclass
class PatternOutcome:
    """Store outcome data for a detected pattern."""
    pattern_name: str
    direction: str  # 'bullish' or 'bearish'
    pattern_price: float
    pattern_date: str
    confidence: float
    pattern_index: int  # Index in dataframe for reference
    
    # Daily prices during each gap period
    daily_prices_1d: List[float] = field(default_factory=list)
    daily_prices_3d: List[float] = field(default_factory=list)
    daily_prices_7d: List[float] = field(default_factory=list)
    daily_prices_14d: List[float] = field(default_factory=list)
    daily_prices_30d: List[float] = field(default_factory=list)
    
    # Direction outcomes (True = pattern prediction was correct)
    bullish_1d: bool = np.nan
    bullish_3d: bool = np.nan
    bullish_7d: bool = np.nan
    bullish_14d: bool = np.nan
    bullish_30d: bool = np.nan


    # Direction outcomes (True = pattern prediction was correct)
    price_1d: float = np.nan
    price_3d: float = np.nan
    price_7d: float = np.nan
    price_14d: float = np.nan
    price_30d: float = np.nan
 
 
@dataclass
class PatternStats:
    """Statistics for a single pattern."""
    pattern_name: str
    direction: str
    
    # Counts
    total_occurrences: int
    high_conf_count: int  # >= conf_threshold
    
    # Prediction accuracy rates (direction-aware)
    accuracy_rate_1d: float
    accuracy_rate_3d: float
    accuracy_rate_7d: float
    accuracy_rate_14d: float
    accuracy_rate_30d: float
    
    # Average maximum return within each period
    # (average of the max daily return for each pattern occurrence)
    avg_max_return_1d: float
    avg_max_return_3d: float
    avg_max_return_7d: float
    avg_max_return_14d: float
    avg_max_return_30d: float
    
    # Win rate (% of occurrences that had positive max return in correct direction)
    win_rate_1d: float
    win_rate_3d: float
    win_rate_7d: float
    win_rate_14d: float
    win_rate_30d: float
    
    # Expected value (avg_max_return * win_rate)
    expected_value_1d: float
    expected_value_3d: float
    expected_value_7d: float
    expected_value_14d: float
    expected_value_30d: float
    
    # Sharpe ratio proxy (avg_max_return / std of max returns)
    sharpe_proxy_1d: float
    sharpe_proxy_3d: float
    sharpe_proxy_7d: float
    sharpe_proxy_14d: float
    sharpe_proxy_30d: float
 
 
@dataclass
class StockAnalysisResult:
    """Complete analysis result for a single stock."""
    stock_name: str
    n_candles: int
    n_patterns_detected: int
    date_range: Tuple[str, str]
    
    # Pattern statistics by name and direction
    pattern_stats: Dict[str, PatternStats]
    
    # Raw outcomes for detailed analysis
    outcomes: List[PatternOutcome]
    
    # Overall statistics
    overall_accuracy_rate_1d: float
    overall_accuracy_rate_3d: float
    overall_accuracy_rate_7d: float
    overall_accuracy_rate_14d: float
    overall_accuracy_rate_30d: float

# =========================
# SINGLE STOCK ANALYSIS
# =========================

def analyze_candlestick_patterns(
    df: pd.DataFrame,
    detect_func,
    stock_name: str = "Stock",
    day_gaps: List[int] = [1, 3, 7, 14, 30],
    min_conf_threshold: float = 0.0,
    min_price_change_pct: float = 0.01,  # 1% for bullish/bearish classification
    use_valid_only: bool = True,
    focus_patterns: Optional[List[str]] = None,
    calculate_sharpe: bool = True,
    debug: bool = False
) -> StockAnalysisResult:
    """
    Analyze candlestick pattern prediction efficiency.
    
    CORRECTED: 
    - Stores all daily prices during each gap period
    - Calculates MAXIMUM daily return within each period
    - Averages the maximum returns across all pattern occurrences
    - Direction-aware win rate and accuracy calculations
    
    Parameters:
    -----------
    df : pd.DataFrame
        OHLC data with columns ['open', 'high', 'low', 'close']
    detect_func : callable
        Function to detect patterns (e.g., detect_candles_claude)
    stock_name : str
        Name/ticker of the stock
    day_gaps : List[int]
        Days to look forward (default [1, 3, 7, 14, 30])
    min_conf_threshold : float
        Minimum confidence to include in analysis (0.0-1.0)
    min_price_change_pct : float
        Minimum % change to classify as bullish/bearish
    use_valid_only : bool
        If True, use only "_valid" patterns. If False, use all patterns.
    focus_patterns : List[str], optional
        If provided, only analyze these patterns
    calculate_sharpe : bool
        Calculate Sharpe ratio proxy (return / volatility)
    debug : bool
        Print detailed debugging info
    
    Returns:
    --------
    StockAnalysisResult with pattern statistics and outcomes
    """
    
    # Detect patterns
    df_detected = detect_func(df)
    df_detected = df_detected.reset_index(drop=True)
    
    if debug:
        print(f"\n{'='*60}")
        print(f"Analyzing {stock_name} | {len(df_detected)} candles")
        print(f"{'='*60}")
    
    # Collect outcomes
    outcomes = []
    
    # Pattern columns to analyze
    all_patterns = [
        "hammer", "hanging_man", "shooting_star",
        "doji", "gravestone_doji", "dragonfly_doji", "long_legged_doji",
        "bullish_engulfing", "bearish_engulfing",
        "bullish_harami",
        "piercing_line", "dark_cloud_cover",
        "morning_star", "evening_star",
        "long_day", "short_day"
    ]
    
    # Filter patterns if focus list provided
    if focus_patterns:
        patterns_to_check = [p for p in all_patterns if p in focus_patterns]
    else:
        patterns_to_check = all_patterns
    
    # Process each candle
    for i in range(len(df_detected)):
        row = df_detected.iloc[i]
        
        # Get all daily prices for each gap period
        daily_prices_by_gap = {}
        for gap in day_gaps:
            prices = []
            for day in range(1, gap + 1):
                future_idx = i + day
                if future_idx < len(df_detected):
                    prices.append(df_detected.iloc[future_idx]["close"])
            daily_prices_by_gap[gap] = prices if prices else []
        
        # Check each pattern
        for pattern_name in patterns_to_check:
            # Skip if pattern not detected
            if not row.get(pattern_name, False):
                continue
            
            # Determine which confidence column to use
            if use_valid_only:
                valid_col = f"{pattern_name}_valid"
                conf_col = f"{pattern_name}_valid_conf"
                
                if not row.get(valid_col, False):
                    continue
            else:
                conf_col = f"{pattern_name}_conf"
            
            conf = row.get(conf_col, 0.0)
            
            # Skip if below confidence threshold
            if conf < min_conf_threshold:
                continue
            
            # Determine pattern direction (bullish vs bearish)
            if pattern_name in ["hammer", "bullish_engulfing", "morning_star", 
                               "piercing_line", "bullish_harami"]:
                direction = "bullish"
            elif pattern_name in ["hanging_man", "shooting_star", "bearish_engulfing", 
                                 "evening_star", "dark_cloud_cover"]:
                direction = "bearish"
            elif pattern_name in ["doji", "gravestone_doji", "dragonfly_doji", 
                                 "long_legged_doji", "short_day", "long_day"]:
                # Neutral patterns — use momentum/context to infer
                momentum = row.get("momentum_ma", np.nan)
                if not np.isnan(momentum):
                    direction = "bullish" if momentum > 0 else "bearish"
                else:
                    direction = "bullish" if row["close"] > row["open"] else "bearish"
            else:
                continue
            
            # Current price (pattern price)
            current_price = row["close"]
            
            # Create outcome record with daily prices and future prices
            outcome = PatternOutcome(
                pattern_name=pattern_name,
                direction=direction,
                pattern_price=current_price,
                pattern_date=str(df_detected.index[i]) if hasattr(df_detected.index[i], '__str__') else f"row_{i}",
                confidence=conf,
                pattern_index=i,
                daily_prices_1d=daily_prices_by_gap.get(1, []),
                daily_prices_3d=daily_prices_by_gap.get(3, []),
                daily_prices_7d=daily_prices_by_gap.get(7, []),
                daily_prices_14d=daily_prices_by_gap.get(14, []),
                daily_prices_30d=daily_prices_by_gap.get(30, []),
                price_1d=daily_prices_by_gap.get(1, [])[-1] if daily_prices_by_gap.get(1) else np.nan,
                price_3d=daily_prices_by_gap.get(3, [])[-1] if daily_prices_by_gap.get(3) else np.nan,
                price_7d=daily_prices_by_gap.get(7, [])[-1] if daily_prices_by_gap.get(7) else np.nan,
                price_14d=daily_prices_by_gap.get(14, [])[-1] if daily_prices_by_gap.get(14) else np.nan,
                price_30d=daily_prices_by_gap.get(30, [])[-1] if daily_prices_by_gap.get(30) else np.nan,
            )
            
            outcomes.append(outcome)
    
    if debug:
        print(f"Total patterns detected: {len(outcomes)}")
    
    # Aggregate statistics
    pattern_stats = {}
    
    for pattern_name in patterns_to_check:
        for direction in ["bullish", "bearish"]:
            key = f"{pattern_name}_{direction}"
            
            # Filter outcomes for this pattern and direction
            pattern_outcomes = [
                o for o in outcomes 
                if o.pattern_name == pattern_name and o.direction == direction
            ]
            
            if not pattern_outcomes:
                continue
            
            n_total = len(pattern_outcomes)
            n_high_conf = sum(1 for o in pattern_outcomes if o.confidence >= min_conf_threshold)
            
            # Calculate statistics for each gap
            stats_by_gap = {}
            for gap in day_gaps:
                daily_prices_attr = f"daily_prices_{gap}d"
                
                # Collect max returns for this gap across all pattern occurrences
                max_returns = []
                accuracy_count = 0
                
                for outcome in pattern_outcomes:
                    daily_prices = getattr(outcome, daily_prices_attr, [])
                    
                    if not daily_prices:
                        continue
                    
                    # Calculate returns for each day
                    daily_returns = [
                        (price - outcome.pattern_price) / outcome.pattern_price * 100
                        for price in daily_prices
                    ]
                    
                    if not daily_returns:
                        continue
                    
                    # Get maximum return in this period
                    max_return = np.max(daily_returns)
                    max_returns.append(max_return)
                    
                    # ===== DIRECTION-AWARE ACCURACY CHECK =====
                    # For bullish: accurate if max return is positive (price went up)
                    # For bearish: accurate if max return is negative (price went down)
                    if direction == "bullish":
                        if max_return > min_price_change_pct:
                            accuracy_count += 1
                    else:  # bearish
                        if max_return < -min_price_change_pct:
                            accuracy_count += 1
                
                if not max_returns:
                    stats_by_gap[gap] = {
                        "accuracy_rate": np.nan,
                        "avg_max_return": np.nan,
                        "win_rate": np.nan,
                        "sharpe": np.nan
                    }
                    continue
                
                # ===== CALCULATE METRICS =====
                
                # Accuracy rate: % of occurrences where pattern prediction was correct
                accuracy_rate = accuracy_count / len(max_returns)
                
                # Average maximum return: mean of max returns per occurrence
                avg_max_return = np.mean(max_returns)
                
                # Win rate: % of occurrences with profitable max return
                # (positive for bullish, negative for bearish)
                if direction == "bullish":
                    win_count = sum(1 for r in max_returns if r > 0)
                else:  # bearish
                    win_count = sum(1 for r in max_returns if r < 0)
                
                win_rate = win_count / len(max_returns) if max_returns else 0.0
                
                # Sharpe ratio proxy: avg_max_return / std(max_returns)
                sharpe_proxy = np.nan
                if calculate_sharpe and len(max_returns) > 1:
                    std_return = np.std(max_returns)
                    sharpe_proxy = avg_max_return / std_return if std_return > 0 else 0.0
                
                stats_by_gap[gap] = {
                    "accuracy_rate": accuracy_rate,
                    "avg_max_return": avg_max_return,
                    "win_rate": win_rate,
                    "sharpe": sharpe_proxy
                }
            
            # Create pattern stats
            pat_stat = PatternStats(
                pattern_name=pattern_name,
                direction=direction,
                total_occurrences=n_total,
                high_conf_count=n_high_conf,
                accuracy_rate_1d=stats_by_gap.get(1, {}).get("accuracy_rate", 0.0),
                accuracy_rate_3d=stats_by_gap.get(3, {}).get("accuracy_rate", 0.0),
                accuracy_rate_7d=stats_by_gap.get(7, {}).get("accuracy_rate", 0.0),
                accuracy_rate_14d=stats_by_gap.get(14, {}).get("accuracy_rate", 0.0),
                accuracy_rate_30d=stats_by_gap.get(30, {}).get("accuracy_rate", 0.0),
                avg_max_return_1d=stats_by_gap.get(1, {}).get("avg_max_return", 0.0),
                avg_max_return_3d=stats_by_gap.get(3, {}).get("avg_max_return", 0.0),
                avg_max_return_7d=stats_by_gap.get(7, {}).get("avg_max_return", 0.0),
                avg_max_return_14d=stats_by_gap.get(14, {}).get("avg_max_return", 0.0),
                avg_max_return_30d=stats_by_gap.get(30, {}).get("avg_max_return", 0.0),
                win_rate_1d=stats_by_gap.get(1, {}).get("win_rate", 0.0),
                win_rate_3d=stats_by_gap.get(3, {}).get("win_rate", 0.0),
                win_rate_7d=stats_by_gap.get(7, {}).get("win_rate", 0.0),
                win_rate_14d=stats_by_gap.get(14, {}).get("win_rate", 0.0),
                win_rate_30d=stats_by_gap.get(30, {}).get("win_rate", 0.0),
                expected_value_1d=stats_by_gap.get(1, {}).get("avg_max_return", 0.0) * 
                                 stats_by_gap.get(1, {}).get("win_rate", 0.0),
                expected_value_3d=stats_by_gap.get(3, {}).get("avg_max_return", 0.0) * 
                                 stats_by_gap.get(3, {}).get("win_rate", 0.0),
                expected_value_7d=stats_by_gap.get(7, {}).get("avg_max_return", 0.0) * 
                                 stats_by_gap.get(7, {}).get("win_rate", 0.0),
                expected_value_14d=stats_by_gap.get(14, {}).get("avg_max_return", 0.0) * 
                                  stats_by_gap.get(14, {}).get("win_rate", 0.0),
                expected_value_30d=stats_by_gap.get(30, {}).get("avg_max_return", 0.0) * 
                                  stats_by_gap.get(30, {}).get("win_rate", 0.0),
                sharpe_proxy_1d=stats_by_gap.get(1, {}).get("sharpe", 0.0),
                sharpe_proxy_3d=stats_by_gap.get(3, {}).get("sharpe", 0.0),
                sharpe_proxy_7d=stats_by_gap.get(7, {}).get("sharpe", 0.0),
                sharpe_proxy_14d=stats_by_gap.get(14, {}).get("sharpe", 0.0),
                sharpe_proxy_30d=stats_by_gap.get(30, {}).get("sharpe", 0.0),
            )
            pattern_stats[key] = pat_stat
    
    # Calculate overall statistics
    overall_accuracy_rate_1d = np.nan
    overall_accuracy_rate_3d = np.nan
    overall_accuracy_rate_7d = np.nan
    overall_accuracy_rate_14d = np.nan
    overall_accuracy_rate_30d = np.nan
    
    if outcomes:
        # For overall stats, check if pattern prediction was correct across all patterns
        for gap, gap_label in [(1, '1d'), (3, '3d'), (7, '7d'), (14, '14d'), (30, '30d')]:
            correct_count = 0
            total_count = 0
            
            for outcome in outcomes:
                daily_prices = getattr(outcome, f"daily_prices_{gap}d", [])
                if not daily_prices:
                    continue
                
                total_count += 1
                daily_returns = [
                    (price - outcome.pattern_price) / outcome.pattern_price * 100
                    for price in daily_prices
                ]
                
                max_return = np.max(daily_returns)
                
                # Check if prediction was correct
                if outcome.direction == "bullish":
                    if max_return > min_price_change_pct:
                        correct_count += 1
                else:  # bearish
                    if max_return < -min_price_change_pct:
                        correct_count += 1
            
            accuracy = correct_count / total_count if total_count > 0 else np.nan
            if gap == 1:
                overall_accuracy_rate_1d = accuracy
            elif gap == 3:
                overall_accuracy_rate_3d = accuracy
            elif gap == 7:
                overall_accuracy_rate_7d = accuracy
            elif gap == 14:
                overall_accuracy_rate_14d = accuracy
            elif gap == 30:
                overall_accuracy_rate_30d = accuracy
    
    return StockAnalysisResult(
        stock_name=stock_name,
        n_candles=len(df_detected),
        n_patterns_detected=len(outcomes),
        date_range=(str(df_detected.index[0]), str(df_detected.index[-1])),
        pattern_stats=pattern_stats,
        outcomes=outcomes,
        overall_accuracy_rate_1d=overall_accuracy_rate_1d,
        overall_accuracy_rate_3d=overall_accuracy_rate_3d,
        overall_accuracy_rate_7d=overall_accuracy_rate_7d,
        overall_accuracy_rate_14d=overall_accuracy_rate_14d,
        overall_accuracy_rate_30d=overall_accuracy_rate_30d,
    )
 
 
# =========================
# UTILITY FUNCTIONS
# =========================
 
def pattern_stats_to_dataframe(result: StockAnalysisResult) -> pd.DataFrame:
    """Convert pattern statistics to a readable DataFrame."""
    rows = []
    for key, stat in result.pattern_stats.items():
        rows.append({
            "Pattern": f"{stat.pattern_name} ({stat.direction})",
            "Count": stat.total_occurrences,
            "HighConf": stat.high_conf_count,
            "Accuracy_7d": f"{stat.accuracy_rate_7d:.1%}",
            "AvgMaxRet_7d": f"{stat.avg_max_return_7d:.2f}%",
            "WinRate_7d": f"{stat.win_rate_7d:.1%}",
            "ExpVal_7d": f"{stat.expected_value_7d:.2f}%",
            "Accuracy_14d": f"{stat.accuracy_rate_14d:.1%}",
            "AvgMaxRet_14d": f"{stat.avg_max_return_14d:.2f}%",
            "WinRate_14d": f"{stat.win_rate_14d:.1%}",
            "ExpVal_14d": f"{stat.expected_value_14d:.2f}%",
            "Accuracy_30d": f"{stat.accuracy_rate_30d:.1%}",
            "AvgMaxRet_30d": f"{stat.avg_max_return_30d:.2f}%",
            "WinRate_30d": f"{stat.win_rate_30d:.1%}",
            "ExpVal_30d": f"{stat.expected_value_30d:.2f}%",
        })
    return pd.DataFrame(rows)

# =========================
# MULTI-STOCK ANALYSIS
# =========================

def analyze_multiple_stocks(
    stock_dataframes: Dict[str, object],
    detect_func,
    day_gaps: List[int] = [7, 14, 30],
    min_conf_threshold: float = 0.0,
    min_price_change_pct: float = 0.01,
    use_valid_only: bool = True,
    focus_patterns: List[str] = None,
    calculate_sharpe: bool = True,
    aggregation_method: str = "weighted",  # "weighted", "simple", "median"
    min_pattern_count: int = 5,  # Minimum occurrences to include in aggregation
    debug: bool = False
) -> Dict:
    """
    Analyze multiple stocks and aggregate results.
    
    CORRECTED: Uses accuracy_rate, win_rate, avg_max_return metrics
    Supports weighted, simple mean, and median aggregation
    
    Parameters:
    -----------
    stock_dataframes : Dict[str, pd.DataFrame]
        Dictionary of {stock_name: df}
    detect_func : callable
        Pattern detection function
    day_gaps : List[int]
        Days to look forward (default [7, 14, 30])
    min_conf_threshold : float
        Minimum confidence threshold
    min_price_change_pct : float
        Minimum price change for accuracy/win rate classification
    use_valid_only : bool
        Use only valid patterns
    focus_patterns : List[str], optional
        Patterns to focus on
    calculate_sharpe : bool
        Calculate Sharpe ratio
    aggregation_method : str
        How to combine results: "weighted" (by count), "simple" (mean), "median"
    min_pattern_count : int
        Minimum occurrences to include in aggregation
    debug : bool
        Print debug info
    
    Returns:
    --------
    Dictionary with:
        - "individual_results": List of StockAnalysisResult
        - "aggregate_stats": Aggregated pattern statistics
        - "consensus_patterns": High-confidence patterns across stocks
    """
    
    # Analyze individual stocks
    results = []
    for stock_name, df in stock_dataframes.items():
        result = analyze_candlestick_patterns(  # ✓ Correct function
            df=df,
            detect_func=detect_func,
            stock_name=stock_name,
            day_gaps=day_gaps,
            min_conf_threshold=min_conf_threshold,
            min_price_change_pct=min_price_change_pct,
            use_valid_only=use_valid_only,
            focus_patterns=focus_patterns,
            calculate_sharpe=calculate_sharpe,
            debug=debug
        )
        results.append(result)

        # print(result)
    
    # Aggregate statistics
    aggregate_stats = defaultdict(lambda: {
        "total_occurrences": 0,
        "accuracy_rates_1d": [],
        "accuracy_rates_3d": [],
        "accuracy_rates_7d": [],
        "accuracy_rates_14d": [],
        "accuracy_rates_30d": [],
        "win_rates_1d": [],
        "win_rates_3d": [],
        "win_rates_7d": [],
        "win_rates_14d": [],
        "win_rates_30d": [],
        "avg_max_returns_1d": [],
        "avg_max_returns_3d": [],
        "avg_max_returns_7d": [],
        "avg_max_returns_14d": [],
        "avg_max_returns_30d": [],
        "pattern_counts": [],  # for weighting
        "results_count": 0  # Number of stocks
    })
    
    for result in results:
        for key, pat_stat in result.pattern_stats.items():
            # Skip if pattern count is below minimum
            if pat_stat.total_occurrences < min_pattern_count:
                continue
            
            agg = aggregate_stats[key]
            agg["total_occurrences"] += pat_stat.total_occurrences
            
            # Collect accuracy rates from each stock
            agg["accuracy_rates_1d"].append(pat_stat.accuracy_rate_1d)
            agg["accuracy_rates_3d"].append(pat_stat.accuracy_rate_3d)
            agg["accuracy_rates_7d"].append(pat_stat.accuracy_rate_7d)
            agg["accuracy_rates_14d"].append(pat_stat.accuracy_rate_14d)
            agg["accuracy_rates_30d"].append(pat_stat.accuracy_rate_30d)
            
            # Collect win rates from each stock
            agg["win_rates_1d"].append(pat_stat.win_rate_1d)
            agg["win_rates_3d"].append(pat_stat.win_rate_3d)
            agg["win_rates_7d"].append(pat_stat.win_rate_7d)
            agg["win_rates_14d"].append(pat_stat.win_rate_14d)
            agg["win_rates_30d"].append(pat_stat.win_rate_30d)
            
            # Collect average max returns from each stock
            agg["avg_max_returns_1d"].append(pat_stat.avg_max_return_1d)
            agg["avg_max_returns_3d"].append(pat_stat.avg_max_return_3d)
            agg["avg_max_returns_7d"].append(pat_stat.avg_max_return_7d)
            agg["avg_max_returns_14d"].append(pat_stat.avg_max_return_14d)
            agg["avg_max_returns_30d"].append(pat_stat.avg_max_return_30d)
            
            # Weight by pattern count for weighted aggregation
            agg["pattern_counts"].append(pat_stat.total_occurrences)
            agg["results_count"] += 1
    
    # Aggregate metrics using chosen method
    for key, agg in aggregate_stats.items():
        if agg["results_count"] > 0:
            if aggregation_method == "weighted":
                # Weighted average by pattern count
                weights = np.array(agg["pattern_counts"])
                total_weight = np.sum(weights)
                
                # Accuracy rates (weighted)
                agg["aggregated_accuracy_rate_1d"] = np.average(agg["accuracy_rates_1d"], weights=weights) if agg["accuracy_rates_1d"] else 0.0
                agg["aggregated_accuracy_rate_3d"] = np.average(agg["accuracy_rates_3d"], weights=weights) if agg["accuracy_rates_3d"] else 0.0
                agg["aggregated_accuracy_rate_7d"] = np.average(agg["accuracy_rates_7d"], weights=weights) if agg["accuracy_rates_7d"] else 0.0
                agg["aggregated_accuracy_rate_14d"] = np.average(agg["accuracy_rates_14d"], weights=weights) if agg["accuracy_rates_14d"] else 0.0
                agg["aggregated_accuracy_rate_30d"] = np.average(agg["accuracy_rates_30d"], weights=weights) if agg["accuracy_rates_30d"] else 0.0
                
                # Win rates (weighted)
                if agg["win_rates_1d"]:
                    agg["aggregated_win_rate_1d"] = np.average(agg["win_rates_1d"], weights=weights)
                else:
                    agg["aggregated_win_rate_1d"] = 0.0
                agg["aggregated_win_rate_3d"] = np.average(agg["win_rates_3d"]) if agg["win_rates_3d"] else 0.0
                agg["aggregated_win_rate_7d"] = np.average(agg["win_rates_7d"]) if agg["win_rates_7d"] else 0.0
                agg["aggregated_win_rate_14d"] = np.average(agg["win_rates_14d"]) if agg["win_rates_14d"] else 0.0
                agg["aggregated_win_rate_30d"] = np.average(agg["win_rates_30d"]) if agg["win_rates_30d"] else 0.0

                # Average max returns (weighted)
                agg["aggregated_avg_max_return_1d"] = np.average(agg["avg_max_returns_1d"], weights=weights) if agg["avg_max_returns_1d"] else 0.0
                agg["aggregated_avg_max_return_3d"] = np.average(agg["avg_max_returns_3d"], weights=weights) if agg["avg_max_returns_3d"] else 0.0
                agg["aggregated_avg_max_return_7d"] = np.average(agg["avg_max_returns_7d"], weights=weights) if agg["avg_max_returns_7d"] else 0.0
                agg["aggregated_avg_max_return_14d"] = np.average(agg["avg_max_returns_14d"], weights=weights) if agg["avg_max_returns_14d"] else 0.0
                agg["aggregated_avg_max_return_30d"] = np.average(agg["avg_max_returns_30d"], weights=weights) if agg["avg_max_returns_30d"] else 0.0
                
            elif aggregation_method == "median":
                # Median across stocks
                agg["aggregated_accuracy_rate_1d"] = np.median(agg["accuracy_rates_1d"]) if agg["accuracy_rates_1d"] else 0.0
                agg["aggregated_accuracy_rate_3d"] = np.median(agg["accuracy_rates_3d"]) if agg["accuracy_rates_3d"] else 0.0
                agg["aggregated_accuracy_rate_7d"] = np.median(agg["accuracy_rates_7d"]) if agg["accuracy_rates_7d"] else 0.0
                agg["aggregated_accuracy_rate_14d"] = np.median(agg["accuracy_rates_14d"]) if agg["accuracy_rates_14d"] else 0.0
                agg["aggregated_accuracy_rate_30d"] = np.median(agg["accuracy_rates_30d"]) if agg["accuracy_rates_30d"] else 0.0
                
                agg["aggregated_win_rate_1d"] = np.median(agg["win_rates_1d"]) if agg["win_rates_1d"] else 0.0
                agg["aggregated_win_rate_3d"] = np.median(agg["win_rates_3d"]) if agg["win_rates_3d"] else 0.0
                agg["aggregated_win_rate_7d"] = np.median(agg["win_rates_7d"]) if agg["win_rates_7d"] else 0.0
                agg["aggregated_win_rate_14d"] = np.median(agg["win_rates_14d"]) if agg["win_rates_14d"] else 0.0
                agg["aggregated_win_rate_30d"] = np.median(agg["win_rates_30d"]) if agg["win_rates_30d"] else 0.0
                
                agg["aggregated_avg_max_return_1d"] = np.median(agg["avg_max_returns_1d"]) if agg["avg_max_returns_1d"] else 0.0
                agg["aggregated_avg_max_return_3d"] = np.median(agg["avg_max_returns_3d"]) if agg["avg_max_returns_3d"] else 0.0
                agg["aggregated_avg_max_return_7d"] = np.median(agg["avg_max_returns_7d"]) if agg["avg_max_returns_7d"] else 0.0
                agg["aggregated_avg_max_return_14d"] = np.median(agg["avg_max_returns_14d"]) if agg["avg_max_returns_14d"] else 0.0
                agg["aggregated_avg_max_return_30d"] = np.median(agg["avg_max_returns_30d"]) if agg["avg_max_returns_30d"] else 0.0
                
            else:  # simple mean
                agg["aggregated_accuracy_rate_1d"] = np.mean(agg["accuracy_rates_1d"]) if agg["accuracy_rates_1d"] else 0.0
                agg["aggregated_accuracy_rate_3d"] = np.mean(agg["accuracy_rates_3d"]) if agg["accuracy_rates_3d"] else 0.0
                agg["aggregated_accuracy_rate_7d"] = np.mean(agg["accuracy_rates_7d"]) if agg["accuracy_rates_7d"] else 0.0
                agg["aggregated_accuracy_rate_14d"] = np.mean(agg["accuracy_rates_14d"]) if agg["accuracy_rates_14d"] else 0.0
                agg["aggregated_accuracy_rate_30d"] = np.mean(agg["accuracy_rates_30d"]) if agg["accuracy_rates_30d"] else 0.0
                
                agg["aggregated_win_rate_1d"] = np.mean(agg["win_rates_1d"]) if agg["win_rates_1d"] else 0.0
                agg["aggregated_win_rate_3d"] = np.mean(agg["win_rates_3d"]) if agg["win_rates_3d"] else 0.0
                agg["aggregated_win_rate_7d"] = np.mean(agg["win_rates_7d"]) if agg["win_rates_7d"] else 0.0
                agg["aggregated_win_rate_14d"] = np.mean(agg["win_rates_14d"]) if agg["win_rates_14d"] else 0.0
                agg["aggregated_win_rate_30d"] = np.mean(agg["win_rates_30d"]) if agg["win_rates_30d"] else 0.0
                
                agg["aggregated_avg_max_return_1d"] = np.mean(agg["avg_max_returns_1d"]) if agg["avg_max_returns_1d"] else 0.0
                agg["aggregated_avg_max_return_3d"] = np.mean(agg["avg_max_returns_3d"]) if agg["avg_max_returns_3d"] else 0.0
                agg["aggregated_avg_max_return_7d"] = np.mean(agg["avg_max_returns_7d"]) if agg["avg_max_returns_7d"] else 0.0
                agg["aggregated_avg_max_return_14d"] = np.mean(agg["avg_max_returns_14d"]) if agg["avg_max_returns_14d"] else 0.0
                agg["aggregated_avg_max_return_30d"] = np.mean(agg["avg_max_returns_30d"]) if agg["avg_max_returns_30d"] else 0.0
        
        # Stock consistency (how many stocks showed this pattern)
        agg["stock_consistency"] = agg["results_count"] / len(results) if len(results) > 0 else 0
    
    # Identify consensus patterns (high consistency across stocks)
    consensus_patterns = {
        k: v for k, v in aggregate_stats.items()
        if v["stock_consistency"] >= 0.5 and v["total_occurrences"] >= min_pattern_count * len(results) / 2
    }
    
    return {
        "individual_results": results,
        "aggregate_stats": dict(aggregate_stats),
        "consensus_patterns": consensus_patterns,
        "num_stocks": len(results),
        "parameters": {
            "day_gaps": day_gaps,
            "min_conf_threshold": min_conf_threshold,
            "min_price_change_pct": min_price_change_pct,
            "use_valid_only": use_valid_only,
            "aggregation_method": aggregation_method,
            "min_pattern_count": min_pattern_count,
        }
    }

# =========================
# REPORTING & UTILITIES
# =========================

def pattern_stats_to_dataframe(result: StockAnalysisResult) -> pd.DataFrame:
    """Convert pattern statistics to a readable DataFrame."""
    rows = []
    for key, stat in result.pattern_stats.items():
        rows.append({
            "Pattern": f"{stat.pattern_name} ({stat.direction})",
            "Count": stat.total_occurrences,
            "HighConf": stat.high_conf_count,
            "Accuracy_7d": f"{stat.accuracy_rate_7d:.1%}",
            "AvgMaxRet_7d": f"{stat.avg_max_return_7d:.2f}%",
            "WinRate_7d": f"{stat.win_rate_7d:.1%}",
            "ExpVal_7d": f"{stat.expected_value_7d:.2f}%",
            "Accuracy_14d": f"{stat.accuracy_rate_14d:.1%}",
            "AvgMaxRet_14d": f"{stat.avg_max_return_14d:.2f}%",
            "WinRate_14d": f"{stat.win_rate_14d:.1%}",
            "ExpVal_14d": f"{stat.expected_value_14d:.2f}%",
            "Accuracy_30d": f"{stat.accuracy_rate_30d:.1%}",
            "AvgMaxRet_30d": f"{stat.avg_max_return_30d:.2f}%",
            "WinRate_30d": f"{stat.win_rate_30d:.1%}",
            "ExpVal_30d": f"{stat.expected_value_30d:.2f}%",
        })
    return pd.DataFrame(rows)
 
 
def filter_patterns_by_criteria(
    result: StockAnalysisResult,
    min_accuracy_rate: float = 0.55,
    min_win_rate: float = 0.50,
    min_count: int = 10,
    gap_days: int = 7
) -> pd.DataFrame:
    """
    Filter patterns by performance criteria.
    
    Parameters:
    -----------
    result : StockAnalysisResult
        Analysis result from analyze_candlestick_patterns
    min_accuracy_rate : float
        Minimum accuracy rate (e.g., 0.55 = 55%)
    min_win_rate : float
        Minimum win rate (e.g., 0.50 = 50%)
    min_count : int
        Minimum number of occurrences
    gap_days : int
        Which time gap to filter by (1, 3, 7, 14, or 30)
    
    Returns:
    --------
    DataFrame of high-quality patterns
    """
    filtered = []
    for key, stat in result.pattern_stats.items():
        if stat.total_occurrences < min_count:
            continue
        
        if gap_days == 1:
            accuracy_rate = stat.accuracy_rate_1d
            win_rate = stat.win_rate_1d
            avg_return = stat.avg_max_return_1d
        elif gap_days == 3:
            accuracy_rate = stat.accuracy_rate_3d
            win_rate = stat.win_rate_3d
            avg_return = stat.avg_max_return_3d
        elif gap_days == 14:
            accuracy_rate = stat.accuracy_rate_14d
            win_rate = stat.win_rate_14d
            avg_return = stat.avg_max_return_14d
        elif gap_days == 30:
            accuracy_rate = stat.accuracy_rate_30d
            win_rate = stat.win_rate_30d
            avg_return = stat.avg_max_return_30d
        else:
            accuracy_rate = stat.accuracy_rate_7d
            win_rate = stat.win_rate_7d
            avg_return = stat.avg_max_return_7d
        
        if accuracy_rate >= min_accuracy_rate and win_rate >= min_win_rate:
            filtered.append({
                "Pattern": f"{stat.pattern_name} ({stat.direction})",
                "Count": stat.total_occurrences,
                "Accuracy": f"{accuracy_rate:.1%}",
                "WinRate": f"{win_rate:.1%}",
                "AvgMaxReturn": f"{avg_return:.2f}%",
            })
    
    return pd.DataFrame(filtered).sort_values("WinRate", ascending=False)
 

def aggregate_stats_to_dataframe(aggregate_stats: Dict) -> pd.DataFrame:
    """Convert aggregated statistics to DataFrame."""
    rows = []
    for key, agg in aggregate_stats.items():
        rows.append({
            "Pattern": key,
            "TotalOccurrences": agg["total_occurrences"],
            "StockConsistency": f"{agg.get('stock_consistency', 0):.1%}",

            "AvgAccuracyRate_7d": f"{agg.get('aggregated_accuracy_rate_7d', 0):.1%}",
            "AvgWinRate_7d": f"{agg.get('aggregated_win_rate_7d', 0):.1%}",
            "AvgMaxReturn_7d": f"{agg.get('aggregated_avg_max_return_7d', 0):.2f}%",

            "AvgAccuracyRate_14d": f"{agg.get('aggregated_accuracy_rate_14d', 0):.1%}",
            "AvgWinRate_14d": f"{agg.get('aggregated_win_rate_14d', 0):.1%}",
            "AvgMaxReturn_14d": f"{agg.get('aggregated_avg_max_return_14d', 0):.2f}%",

            "AvgAccuracyRate_30d": f"{agg.get('aggregated_accuracy_rate_30d', 0):.1%}",
            "AvgWinRate_30d": f"{agg.get('aggregated_win_rate_30d', 0):.1%}",
            "AvgMaxReturn_30d": f"{agg.get('aggregated_avg_max_return_30d', 0):.2f}%",
        })
    return pd.DataFrame(rows)

