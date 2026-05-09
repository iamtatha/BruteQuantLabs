"""
Practical Examples: Pattern Efficiency Analysis

This file contains ready-to-run examples for different use cases.
"""

import pandas as pd
import numpy as np

import sys
from pathlib import Path
import logging

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))



from research_candle_stick.scripts.candle_stick_pattern_efficiency import (
    analyze_candlestick_patterns,
    analyze_multiple_stocks,
    pattern_stats_to_dataframe,
    aggregate_stats_to_dataframe,
    filter_patterns_by_criteria,
)
from analysis_scripts.utils.candles import detect_candles_claude



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
    df.index.name = "date"

    dates = pd.to_datetime(df.index.tolist()).tolist()
    
    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock_code}.NS", '').lower() for c in cols]
    df.columns = cols
    return df, dates, cols


# =========================
# EXAMPLE 1: Single Stock Analysis
# =========================

def example_single_stock(stock_code="TCS"):
    """Basic analysis of one stock."""
    print("\n" + "="*70)
    print(f"EXAMPLE 1: Single Stock Analysis ({stock_code})")
    print("="*70)
    
    # Load data (replace with your actual data)
    df, _, _ = load_data(stock_code=stock_code)

    # Analyze patterns
    result = analyze_candlestick_patterns(
        df=df,
        detect_func=detect_candles_claude,
        stock_name=stock_code,
        day_gaps=[7, 14, 30],
        min_conf_threshold=0.50,
        min_price_change_pct=1.0,
    )
    
    # Print summary
    print(f"\nStock: {result.stock_name}")
    print(f"Candles analyzed: {result.n_candles}")
    print(f"Patterns detected: {result.n_patterns_detected}")
    print(f"Date range: {result.date_range[0]} to {result.date_range[1]}")
    
    # Print overall statistics
    print(f"\nOverall accuracy rates:")
    print(f"  1-day:  {result.overall_accuracy_rate_1d:.1%}")
    print(f"  3-day:  {result.overall_accuracy_rate_3d:.1%}")
    print(f"  7-day:  {result.overall_accuracy_rate_7d:.1%}")
    print(f"  14-day: {result.overall_accuracy_rate_14d:.1%}")
    print(f"  30-day: {result.overall_accuracy_rate_30d:.1%}")

    # Show pattern statistics
    print("\nPattern Statistics:")
    stats_df = pattern_stats_to_dataframe(result)
    print(stats_df.to_string(index=False))
    
    return result


# =========================
# EXAMPLE 2: Find High-Quality Patterns
# =========================

def example_high_quality_patterns(stock_code="TCS"):
    """Find patterns with strong predictive power."""
    print("\n" + "="*70)
    print("EXAMPLE 2: High-Quality Pattern Screening")
    print("="*70)

    df, _, _ = load_data(stock_code=stock_code)

    result = analyze_candlestick_patterns(
        df=df,
        detect_func=detect_candles_claude,
        stock_name=stock_code,
        min_conf_threshold=0.60,
    )

    # Filter patterns: 55%+ accuracy rate, 50%+ win rate, 10+ occurrences
    high_quality = filter_patterns_by_criteria(
        result,
        min_accuracy_rate=0.65,
        min_win_rate=0.60,
        min_count=10,
        gap_days=7
    )
    
    print(f"\nHigh-quality patterns (55%+ accuracy, 50%+ win rate, 10+ occurrences):")
    if len(high_quality) > 0:
        print(high_quality.to_string(index=False))
        
        # Print detailed returns for each time horizon
        print("\nDetailed Average Max Returns:")
        print(f"{'Pattern':<30} {'7d Return':<15} {'14d Return':<15} {'30d Return':<15}")
        print("-" * 75)
        for key, stat in result.pattern_stats.items():
            pattern_name = f"{stat.pattern_name} ({stat.direction})"
            if stat.total_occurrences >= 10:
                print(f"{pattern_name:<30} {stat.avg_max_return_7d:>13.2f}% {stat.avg_max_return_14d:>13.2f}% {stat.avg_max_return_30d:>13.2f}%")
    else:
        print("No patterns meet criteria")
    
    return result, high_quality


# =========================
# EXAMPLE 4: Multi-Stock Analysis
# =========================

def example_multi_stock(stock_codes = ["TCS", "INFY", "WIPRO"]):
    """Analyze multiple stocks and find universal patterns."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Multi-Stock Analysis")
    print("="*70)
    
    # Load multiple stocks
    stock_data = {}
    for stock in stock_codes:
        df, _, _ = load_data(stock_code=stock)
        stock_data[stock] = df

    # Analyze
    result = analyze_multiple_stocks(
        stock_dataframes=stock_data,
        detect_func=detect_candles_claude,
        day_gaps=[7, 14, 30],
        min_pattern_count=10,
    )
    
    print(f"\nAnalyzed {result['num_stocks']} stocks")
    
    # Show individual results
    print("\nIndividual Stock Results:")
    for res in result["individual_results"]:
        print(f"  {res.stock_name}: {res.n_patterns_detected} patterns")
    
    # Show consensus patterns
    print(f"\nConsensus Patterns (appear in 50%+ of stocks):")
    consensus_df = aggregate_stats_to_dataframe(result["consensus_patterns"])
    if len(consensus_df) > 0:
        print(consensus_df.to_string(index=False))
    else:
        print("No consensus patterns found")
    
    return result


# =========================
# EXAMPLE 5: Time Decay Analysis
# =========================

def example_time_decay(stock_code = "TCS"):
    """Analyze how pattern predictability decays over time."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Time Decay Analysis (Pattern Power Over Time)")
    print("="*70)

    df, _, _ = load_data(stock_code=stock_code)

    # Analyze at multiple time horizons (skip 1d, 3d - not enough future data)
    result = analyze_candlestick_patterns(
        df=df,
        detect_func=detect_candles_claude,
        stock_name=stock_code,
        day_gaps=[7, 14, 30],  # Skip 1, 3 - not enough future data
    )
    
    print(f"\nAnalyzed {result.n_patterns_detected} patterns over {result.n_candles} candles")
    
    print("\nOverall Pattern Accuracy by Time Horizon:")
    print(f"{'Gap':<8} {'Accuracy':<15}")
    print("-" * 23)
    if not np.isnan(result.overall_accuracy_rate_7d):
        print(f"{'7d':<8} {result.overall_accuracy_rate_7d:.1%}")
    if not np.isnan(result.overall_accuracy_rate_14d):
        print(f"{'14d':<8} {result.overall_accuracy_rate_14d:.1%}")
    if not np.isnan(result.overall_accuracy_rate_30d):
        print(f"{'30d':<8} {result.overall_accuracy_rate_30d:.1%}")
    
    # Analyze each pattern across time horizons
    print("\n\nPattern-by-Pattern Time Decay Analysis:")
    print(f"{'Pattern':<35} {'7d Acc':<12} {'14d Acc':<12} {'30d Acc':<12} {'Trend':<10}")
    print("-" * 80)
    
    time_decay_patterns = []
    
    for key, stat in result.pattern_stats.items():
        if stat.total_occurrences < 10:  # Skip patterns with few occurrences
            continue
        
        acc_7d = stat.accuracy_rate_7d
        acc_14d = stat.accuracy_rate_14d
        acc_30d = stat.accuracy_rate_30d
        
        # Determine trend: improving or decaying
        if acc_7d > acc_14d > acc_30d:
            trend = "↓ Decay"
        elif acc_7d < acc_14d < acc_30d:
            trend = "↑ Improve"
        elif acc_14d > acc_7d and acc_14d > acc_30d:
            trend = "Peak 14d"
        else:
            trend = "Mixed"
        
        time_decay_patterns.append({
            "pattern": key,
            "acc_7d": acc_7d,
            "acc_14d": acc_14d,
            "acc_30d": acc_30d,
            "trend": trend,
            "count": stat.total_occurrences
        })
        
        print(f"{key:<35} {acc_7d:>10.1%}  {acc_14d:>10.1%}  {acc_30d:>10.1%}  {trend:<10}")
    
    # Summary analysis
    print("\n\nTime Decay Summary:")
    print(f"{'Gap':<8} {'Avg Accuracy':<20} {'Min':<10} {'Max':<10} {'Std Dev':<10}")
    print("-" * 58)
    
    if time_decay_patterns:
        # 7-day stats
        acc_7d_values = [p["acc_7d"] for p in time_decay_patterns]
        print(f"{'7d':<8} {np.mean(acc_7d_values):>18.1%}  {np.min(acc_7d_values):>8.1%}  {np.max(acc_7d_values):>8.1%}  {np.std(acc_7d_values):>8.1%}")
        
        # 14-day stats
        acc_14d_values = [p["acc_14d"] for p in time_decay_patterns]
        print(f"{'14d':<8} {np.mean(acc_14d_values):>18.1%}  {np.min(acc_14d_values):>8.1%}  {np.max(acc_14d_values):>8.1%}  {np.std(acc_14d_values):>8.1%}")
        
        # 30-day stats
        acc_30d_values = [p["acc_30d"] for p in time_decay_patterns]
        print(f"{'30d':<8} {np.mean(acc_30d_values):>18.1%}  {np.min(acc_30d_values):>8.1%}  {np.max(acc_30d_values):>8.1%}  {np.std(acc_30d_values):>8.1%}")
        
        print("\nInterpretation:")
        avg_7d = np.mean(acc_7d_values)
        avg_14d = np.mean(acc_14d_values)
        avg_30d = np.mean(acc_30d_values)
        
        if avg_7d > avg_14d > avg_30d:
            print("  → Pattern predictive power DECAYS over time (best on day 7)")
        elif avg_7d < avg_14d < avg_30d:
            print("  → Pattern predictive power IMPROVES over time (best on day 30)")
        else:
            print("  → Pattern predictive power is MIXED or VARIABLE")
    
    print("\nTop 3 Most Persistent Patterns (high accuracy across all timeframes):")
    if time_decay_patterns:
        # Calculate consistency across time horizons
        for p in time_decay_patterns:
            p["consistency"] = min(p["acc_7d"], p["acc_14d"], p["acc_30d"])
        
        top_patterns = sorted(time_decay_patterns, key=lambda x: x["consistency"], reverse=True)[:3]
        
        for i, p in enumerate(top_patterns, 1):
            print(f"  {i}. {p['pattern']:<30} Accuracy: 7d={p['acc_7d']:.1%}, 14d={p['acc_14d']:.1%}, 30d={p['acc_30d']:.1%} (Count: {p['count']})")
    
    return result



# =========================
# EXAMPLE 7: Custom Detection Thresholds
# =========================

def example_custom_detection():
    """Use custom pattern detection thresholds."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Custom Pattern Detection Thresholds")
    print("="*70)
    
    df = pd.read_csv("aapl_historical.csv", index_col="date")
    
    # Create custom detection function
    def custom_detect(data):
        return detect_candles_claude(
            data,
            DOJI_THRESHOLD=0.15,           # Looser doji (high vol)
            HAMMER_LOWER_WICK_RATIO=2.0,  # Stricter hammer
            ENGULFING_BODY_MULTIPLIER=1.2, # Stricter engulfing
            LONG_DAY_THRESHOLD=0.65,      # Looser long day
        )
    
    result = analyze_candlestick_patterns(
        df=df,
        detect_func=custom_detect,
        stock_name="AAPL (Custom Detection)",
        min_conf_threshold=0.50,
    )
    
    print(f"\nDetected {result.n_patterns_detected} patterns with custom thresholds")
    print("\nTop patterns by occurrence:")
    
    # Sort by count
    sorted_patterns = sorted(
        result.pattern_stats.items(),
        key=lambda x: x[1].total_occurrences,
        reverse=True
    )
    
    for i, (key, stat) in enumerate(sorted_patterns[:5]):
        print(f"  {i+1}. {stat.pattern_name} ({stat.direction}): {stat.total_occurrences} times")
    
    return result



# =========================
# MAIN: Run Examples
# =========================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CANDLESTICK PATTERN EFFICIENCY ANALYSIS - EXAMPLES")
    print("="*70)
    
    # Uncomment examples to run
    
    example_single_stock()
    example_high_quality_patterns()
    example_multi_stock()
    example_time_decay()
    # example_custom_detection()
    
    print("\n✓ All examples defined. Uncomment in main() to run.")