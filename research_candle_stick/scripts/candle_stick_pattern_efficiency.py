import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
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
    
    # Forward price movements
    price_1d: float
    price_3d: float
    price_7d: float
    price_14d: float
    price_30d: float
    
    # Direction outcomes
    bullish_1d: bool
    bullish_3d: bool
    bullish_7d: bool
    bullish_14d: bool
    bullish_30d: bool


@dataclass
class PatternStats:
    """Statistics for a single pattern."""
    pattern_name: str
    direction: str
    
    # Counts
    total_occurrences: int
    high_conf_count: int  # >= conf_threshold
    
    # Bullish outcome rates
    bullish_rate_7d: float
    bullish_rate_14d: float
    bullish_rate_30d: float
    
    # Average price returns
    avg_return_7d: float
    avg_return_14d: float
    avg_return_30d: float
    
    # Win rate (% profit if traded)
    win_rate_7d: float
    win_rate_14d: float
    win_rate_30d: float
    
    # Expected value (avg return * win rate)
    expected_value_7d: float
    expected_value_14d: float
    expected_value_30d: float
    
    # Sharpe ratio proxy (return / std)
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
    overall_bullish_rate_7d: float
    overall_bullish_rate_14d: float
    overall_bullish_rate_30d: float


# =========================
# SINGLE STOCK ANALYSIS
# =========================

def analyze_candlestick_patterns(
    df: pd.DataFrame,
    detect_func,
    stock_name: str = "Stock",
    day_gaps: List[int] = [7, 14, 30],
    min_conf_threshold: float = 0.0,
    min_price_change_pct: float = 0.01,  # 1% for bullish/bearish classification
    use_valid_only: bool = True,
    focus_patterns: Optional[List[str]] = None,
    calculate_sharpe: bool = True,
    debug: bool = False
) -> StockAnalysisResult:
    """
    Analyze candlestick pattern prediction efficiency.
    
    Parameters:
    -----------
    df : pd.DataFrame
        OHLC data with columns ['open', 'high', 'low', 'close']
    detect_func : callable
        Function to detect patterns (e.g., detect_candles_claude)
    stock_name : str
        Name/ticker of the stock
    day_gaps : List[int]
        Days to look forward (default [7, 14, 30])
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
        
        # Get future prices at each gap
        future_prices = {}
        for gap in day_gaps:
            future_idx = i + gap
            if future_idx < len(df_detected):
                future_prices[gap] = df_detected.iloc[future_idx]["close"]
            else:
                future_prices[gap] = np.nan
        
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
                # Use momentum_ma if available, else use close vs open
                momentum = row.get("momentum_ma", np.nan)
                if not np.isnan(momentum):
                    direction = "bullish" if momentum > 0 else "bearish"
                else:
                    direction = "bullish" if row["close"] > row["open"] else "bearish"
            else:
                continue
            
            # Calculate returns
            current_price = row["close"]
            outcomes_dict = {}
            bullish_flags = {}
            
            for gap in day_gaps:
                future_price = future_prices[gap]
                
                if np.isnan(future_price):
                    outcomes_dict[f"price_{gap}d"] = np.nan
                    bullish_flags[f"bullish_{gap}d"] = np.nan
                    continue
                 
                # Return in %
                ret_pct = (future_price - current_price) / current_price * 100
                outcomes_dict[f"price_{gap}d"] = future_price
                
                # Bullish if return > threshold
                is_bullish = ret_pct > min_price_change_pct
                bullish_flags[f"bullish_{gap}d"] = is_bullish

            
            # Create outcome record
            outcome = PatternOutcome(
                pattern_name=pattern_name,
                direction=direction,
                pattern_price=current_price,
                pattern_date=str(df_detected.index[i]) if hasattr(df_detected.index[i], '__str__') else f"row_{i}",
                confidence=conf,
                price_1d=outcomes_dict.get("price_1d", np.nan),
                price_3d=outcomes_dict.get("price_3d", np.nan),
                price_7d=outcomes_dict.get("price_7d", np.nan),
                price_14d=outcomes_dict.get("price_14d", np.nan),
                price_30d=outcomes_dict.get("price_30d", np.nan),
                bullish_1d=bullish_flags.get("bullish_1d", np.nan),
                bullish_3d=bullish_flags.get("bullish_3d", np.nan),
                bullish_7d=bullish_flags.get("bullish_7d", np.nan),
                bullish_14d=bullish_flags.get("bullish_14d", np.nan),
                bullish_30d=bullish_flags.get("bullish_30d", np.nan),
            )
            outcomes.append(outcome)
    
    if debug:
        print(f"Total patterns detected: {len(outcomes)}")
    
    # Aggregate statistics
    pattern_stats = {}
    
    for pattern_name in patterns_to_check:
        for direction in ["bullish", "bearish"]:
            key = f"{pattern_name}_{direction}"
            
            # Filter outcomes
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
                price_col = f"price_{gap}d"
                bullish_col = f"bullish_{gap}d"
                
                prices = [getattr(o, price_col) for o in pattern_outcomes]
                bullish_flags = [getattr(o, bullish_col) for o in pattern_outcomes]
                
                # Filter out NaN values
                valid_prices = [p for p in prices if not np.isnan(p)]
                valid_bullish = [b for b, p in zip(bullish_flags, prices) if not np.isnan(p)]
                
                if not valid_prices:
                    stats_by_gap[gap] = {
                        "bullish_rate": np.nan,
                        "avg_return": np.nan,
                        "win_rate": np.nan,
                        "sharpe": np.nan
                    }
                    continue
                
                # Calculate returns
                current_prices = [o.pattern_price for o in pattern_outcomes 
                                 if not np.isnan(getattr(o, price_col))]
                returns = [(p - cp) / cp * 100 for p, cp in zip(valid_prices, current_prices)]
                
                bullish_rate = sum(valid_bullish) / len(valid_bullish) if valid_bullish else 0.0
                avg_return = np.mean(returns)
                win_rate = sum(1 for r in returns if r > 0) / len(returns) if returns else 0.0
                
                # Sharpe proxy
                sharpe_proxy = np.nan
                if calculate_sharpe and len(returns) > 1:
                    std_return = np.std(returns)
                    sharpe_proxy = avg_return / std_return if std_return > 0 else 0.0
                
                stats_by_gap[gap] = {
                    "bullish_rate": bullish_rate,
                    "avg_return": avg_return,
                    "win_rate": win_rate,
                    "sharpe": sharpe_proxy
                }
            
            # Create pattern stats
            pat_stat = PatternStats(
                pattern_name=pattern_name,
                direction=direction,
                total_occurrences=n_total,
                high_conf_count=n_high_conf,
                bullish_rate_7d=stats_by_gap.get(7, {}).get("bullish_rate", 0.0),
                bullish_rate_14d=stats_by_gap.get(14, {}).get("bullish_rate", 0.0),
                bullish_rate_30d=stats_by_gap.get(30, {}).get("bullish_rate", 0.0),
                avg_return_7d=stats_by_gap.get(7, {}).get("avg_return", 0.0),
                avg_return_14d=stats_by_gap.get(14, {}).get("avg_return", 0.0),
                avg_return_30d=stats_by_gap.get(30, {}).get("avg_return", 0.0),
                win_rate_7d=stats_by_gap.get(7, {}).get("win_rate", 0.0),
                win_rate_14d=stats_by_gap.get(14, {}).get("win_rate", 0.0),
                win_rate_30d=stats_by_gap.get(30, {}).get("win_rate", 0.0),
                expected_value_7d=stats_by_gap.get(7, {}).get("avg_return", 0.0) * 
                                 stats_by_gap.get(7, {}).get("win_rate", 0.0),
                expected_value_14d=stats_by_gap.get(14, {}).get("avg_return", 0.0) * 
                                  stats_by_gap.get(14, {}).get("win_rate", 0.0),
                expected_value_30d=stats_by_gap.get(30, {}).get("avg_return", 0.0) * 
                                  stats_by_gap.get(30, {}).get("win_rate", 0.0),
                sharpe_proxy_7d=stats_by_gap.get(7, {}).get("sharpe", 0.0),
                sharpe_proxy_14d=stats_by_gap.get(14, {}).get("sharpe", 0.0),
                sharpe_proxy_30d=stats_by_gap.get(30, {}).get("sharpe", 0.0),
            )
            pattern_stats[key] = pat_stat
    
    # Calculate overall statistics
    overall_bullish_rate_7d = np.nan
    overall_bullish_rate_14d = np.nan
    overall_bullish_rate_30d = np.nan
    
    if outcomes:
        valid_7d = [o.bullish_7d for o in outcomes if not np.isnan(o.bullish_7d)]
        valid_14d = [o.bullish_14d for o in outcomes if not np.isnan(o.bullish_14d)]
        valid_30d = [o.bullish_30d for o in outcomes if not np.isnan(o.bullish_30d)]
        
        overall_bullish_rate_7d = sum(valid_7d) / len(valid_7d) if valid_7d else np.nan
        overall_bullish_rate_14d = sum(valid_14d) / len(valid_14d) if valid_14d else np.nan
        overall_bullish_rate_30d = sum(valid_30d) / len(valid_30d) if valid_30d else np.nan
    
    return StockAnalysisResult(
        stock_name=stock_name,
        n_candles=len(df_detected),
        n_patterns_detected=len(outcomes),
        date_range=(str(df_detected.index[0]), str(df_detected.index[-1])),
        pattern_stats=pattern_stats,
        outcomes=outcomes,
        overall_bullish_rate_7d=overall_bullish_rate_7d,
        overall_bullish_rate_14d=overall_bullish_rate_14d,
        overall_bullish_rate_30d=overall_bullish_rate_30d,
    )


# =========================
# MULTI-STOCK ANALYSIS
# =========================

def analyze_multiple_stocks(
    stock_dataframes: Dict[str, pd.DataFrame],
    detect_func,
    day_gaps: List[int] = [7, 14, 30],
    min_conf_threshold: float = 0.0,
    min_price_change_pct: float = 0.01,
    use_valid_only: bool = True,
    focus_patterns: Optional[List[str]] = None,
    calculate_sharpe: bool = True,
    aggregation_method: str = "weighted",  # "weighted", "simple", "median"
    min_pattern_count: int = 5,  # Minimum occurrences to include in aggregation
    debug: bool = False
) -> Dict:
    """
    Analyze multiple stocks and aggregate results.
    
    Parameters:
    -----------
    stock_dataframes : Dict[str, pd.DataFrame]
        Dictionary of {stock_name: df}
    detect_func : callable
        Pattern detection function
    day_gaps : List[int]
        Days to look forward
    min_conf_threshold : float
        Minimum confidence threshold
    min_price_change_pct : float
        Minimum price change for bullish/bearish classification
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
        result = analyze_candlestick_patterns(
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
    
    # Aggregate statistics
    aggregate_stats = defaultdict(lambda: {
        "total_occurrences": 0,
        "total_wins": 0,
        "total_returns": [],
        "confidence_scores": [],
        "bullish_counts": {"7d": 0, "14d": 0, "30d": 0},
        "results_count": 0  # Number of stocks
    })
    
    for result in results:
        for key, pat_stat in result.pattern_stats.items():
            # Skip if pattern count is below minimum
            if pat_stat.total_occurrences < min_pattern_count:
                continue
            
            agg = aggregate_stats[key]
            agg["total_occurrences"] += pat_stat.total_occurrences
            agg["total_wins"] += max(0, int(pat_stat.win_rate_7d * pat_stat.total_occurrences))
            agg["bullish_counts"]["7d"] += int(pat_stat.bullish_rate_7d * pat_stat.total_occurrences)
            agg["bullish_counts"]["14d"] += int(pat_stat.bullish_rate_14d * pat_stat.total_occurrences)
            agg["bullish_counts"]["30d"] += int(pat_stat.bullish_rate_30d * pat_stat.total_occurrences)
            agg["confidence_scores"].append(pat_stat.total_occurrences)  # weight by count
            agg["results_count"] += 1
    
    # Convert aggregated counts to probabilities
    for key, agg in aggregate_stats.items():
        if agg["total_occurrences"] > 0:
            agg["aggregated_win_rate"] = agg["total_wins"] / agg["total_occurrences"]
            agg["aggregated_bullish_rate_7d"] = agg["bullish_counts"]["7d"] / agg["total_occurrences"]
            agg["aggregated_bullish_rate_14d"] = agg["bullish_counts"]["14d"] / agg["total_occurrences"]
            agg["aggregated_bullish_rate_30d"] = agg["bullish_counts"]["30d"] / agg["total_occurrences"]
        
        # Stock consistency (how many stocks showed this pattern)
        agg["stock_consistency"] = agg["results_count"] / len(results)
    
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
            "Bullish_7d": f"{stat.bullish_rate_7d:.1%}",
            "Bullish_14d": f"{stat.bullish_rate_14d:.1%}",
            "Bullish_30d": f"{stat.bullish_rate_30d:.1%}",
            "AvgRet_7d": f"{stat.avg_return_7d:.2f}%",
            "AvgRet_14d": f"{stat.avg_return_14d:.2f}%",
            "AvgRet_30d": f"{stat.avg_return_30d:.2f}%",
            "WinRate_7d": f"{stat.win_rate_7d:.1%}",
            "WinRate_14d": f"{stat.win_rate_14d:.1%}",
            "WinRate_30d": f"{stat.win_rate_30d:.1%}",
            "ExpVal_7d": f"{stat.expected_value_7d:.2f}%",
            "ExpVal_14d": f"{stat.expected_value_14d:.2f}%",
            "ExpVal_30d": f"{stat.expected_value_30d:.2f}%",
        })
    return pd.DataFrame(rows)


def aggregate_stats_to_dataframe(aggregate_stats: Dict) -> pd.DataFrame:
    """Convert aggregated statistics to DataFrame."""
    rows = []
    for key, agg in aggregate_stats.items():
        rows.append({
            "Pattern": key,
            "TotalOccurrences": agg["total_occurrences"],
            "StockConsistency": f"{agg.get('stock_consistency', 0):.1%}",
            "AvgBullishRate_7d": f"{agg.get('aggregated_bullish_rate_7d', 0):.1%}",
            "AvgBullishRate_14d": f"{agg.get('aggregated_bullish_rate_14d', 0):.1%}",
            "AvgBullishRate_30d": f"{agg.get('aggregated_bullish_rate_30d', 0):.1%}",
            "AvgWinRate": f"{agg.get('aggregated_win_rate', 0):.1%}",
        })
    return pd.DataFrame(rows)


def filter_patterns_by_criteria(
    result: StockAnalysisResult,
    min_bullish_rate: float = 0.55,
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
    min_bullish_rate : float
        Minimum bullish rate (e.g., 0.55 = 55%)
    min_win_rate : float
        Minimum win rate (e.g., 0.50 = 50%)
    min_count : int
        Minimum number of occurrences
    gap_days : int
        Which time gap to filter by (7, 14, or 30)
    
    Returns:
    --------
    DataFrame of high-quality patterns
    """
    filtered = []
    for key, stat in result.pattern_stats.items():
        if stat.total_occurrences < min_count:
            continue
        
        if gap_days == 7:
            bullish_rate = stat.bullish_rate_7d
            win_rate = stat.win_rate_7d
        elif gap_days == 14:
            bullish_rate = stat.bullish_rate_14d
            win_rate = stat.win_rate_14d
        else:
            bullish_rate = stat.bullish_rate_30d
            win_rate = stat.win_rate_30d
        
        if bullish_rate >= min_bullish_rate and win_rate >= min_win_rate:
            filtered.append({
                "Pattern": f"{stat.pattern_name} ({stat.direction})",
                "Count": stat.total_occurrences,
                "BullishRate": f"{bullish_rate:.1%}",
                "WinRate": f"{win_rate:.1%}",
                "AvgReturn": f"{stat.avg_return_7d if gap_days == 7 else (stat.avg_return_14d if gap_days == 14 else stat.avg_return_30d):.2f}%",
            })
    
    return pd.DataFrame(filtered).sort_values("WinRate", ascending=False)