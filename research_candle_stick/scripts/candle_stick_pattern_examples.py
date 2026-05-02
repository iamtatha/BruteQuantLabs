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
    print(f"\nOverall bullish rates:")
    print(f"  7-day:  {result.overall_bullish_rate_7d:.1%}")
    print(f"  14-day: {result.overall_bullish_rate_14d:.1%}")
    print(f"  30-day: {result.overall_bullish_rate_30d:.1%}")
    
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
    
    # Filter patterns: 55%+ bullish rate, 50%+ win rate, 10+ occurrences
    high_quality = filter_patterns_by_criteria(
        result,
        min_bullish_rate=0.55,
        min_win_rate=0.50,
        min_count=10,
        gap_days=30
    )
    
    print(f"\nHigh-quality patterns (55%+ bullish, 50%+ win rate, 10+ occurrences):")
    if len(high_quality) > 0:
        print(high_quality.to_string(index=False))
    else:
        print("No patterns meet criteria")
    
    return result, high_quality


# =========================
# EXAMPLE 3: Confidence Threshold Tuning
# =========================

def example_threshold_tuning(stock_code="TCS"):
    """Find optimal confidence threshold."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Confidence Threshold Optimization")
    print("="*70)

    df, _, _ = load_data(stock_code=stock_code)

    thresholds = [0.0, 0.3, 0.5, 0.7, 0.9]
    results = {}
    
    for threshold in thresholds:
        result = analyze_candlestick_patterns(
            df=df,
            detect_func=detect_candles_claude,
            stock_name=stock_code,
            min_conf_threshold=threshold,
        )
        
        # Count high-quality patterns
        high_quality = filter_patterns_by_criteria(
            result,
            min_bullish_rate=0.55,
            min_win_rate=0.50,
            min_count=10,
            gap_days=21
        )
        
        results[threshold] = {
            "total_patterns": result.n_patterns_detected,
            "pattern_types": len(result.pattern_stats),
            "high_quality": len(high_quality),
            "quality_ratio": len(high_quality) / max(1, len(result.pattern_stats)),
        }
    
    # Display results
    print("\nThreshold Analysis:")
    print(f"{'Threshold':<12} {'Total':<10} {'Types':<10} {'HQ':<10} {'Ratio':<10}")
    print("-" * 52)
    for threshold in sorted(results.keys()):
        r = results[threshold]
        print(f"{threshold:<12} {r['total_patterns']:<10} {r['pattern_types']:<10} "
              f"{r['high_quality']:<10} {r['quality_ratio']:.2%}")
    
    # Find optimal
    optimal = max(results.items(), key=lambda x: x[1]["quality_ratio"])
    print(f"\nOptimal threshold: {optimal[0]} (quality ratio: {optimal[1]['quality_ratio']:.1%})")
    
    return results


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

def example_time_decay(stock_code="TCS"):
    """Analyze how pattern predictability decays over time."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Time Decay Analysis (Pattern Power Over Time)")
    print("="*70)

    df, _, _ = load_data(stock_code=stock_code)

    # Analyze at multiple time horizons
    result = analyze_candlestick_patterns(
        df=df,
        detect_func=detect_candles_claude,
        stock_name=stock_code,
        day_gaps=[1, 3, 7, 14, 30],  # Many time horizons
    )

    print(result)
    
    print("\nPattern Predictability by Time Horizon:")
    print(f"{'Gap':<8} {'Overall Bullish':<20} {'Avg Return':<15}")
    print("-" * 43)
    
    # This would require modifying the function to store all gap data
    # For now, show pattern with fixed gaps
    print("(Note: Modify function to store all day_gap statistics)")
    
    return result


# =========================
# EXAMPLE 6: Focused Pattern Analysis
# =========================

def example_focused_patterns(stock_code="TCS"):
    """Analyze only specific patterns of interest."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Focused Pattern Analysis (Reversal Patterns)")
    print("="*70)

    df, _, _ = load_data(stock_code=stock_code)

    # Focus only on reversal patterns
    reversal_patterns = [
        "hammer", "hanging_man", "shooting_star",
        "morning_star", "evening_star"
    ]
    
    result = analyze_candlestick_patterns(
        df=df,
        detect_func=detect_candles_claude,
        stock_name=stock_code,
        focus_patterns=reversal_patterns,
        min_conf_threshold=0.60,
    )
    
    print(f"\nAnalyzed {len(reversal_patterns)} reversal patterns")
    print(f"Found {result.n_patterns_detected} occurrences")
    
    # Show results
    stats_df = pattern_stats_to_dataframe(result)
    print("\nReversal Pattern Statistics:")
    print(stats_df.to_string(index=False))
    
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
# EXAMPLE 8: Detailed Outcome Analysis
# =========================

def example_detailed_outcomes(stock_code="TCS", pattern_name_focus="evening_star"):
    """Examine individual pattern outcomes in detail."""
    print("\n" + "="*70)
    print("EXAMPLE 8: Detailed Pattern Outcome Analysis")
    print("="*70)

    df, _, _ = load_data(stock_code=stock_code)

    result = analyze_candlestick_patterns(
        df=df,
        detect_func=detect_candles_claude,
        stock_name=stock_code,
        min_conf_threshold=0.70,
    )
    
    # Examine outcomes
    print(f"\nTotal outcomes: {len(result.outcomes)}")
    
    # Group by pattern
    from collections import defaultdict
    by_pattern = defaultdict(list)
    for outcome in result.outcomes:
        by_pattern[outcome.pattern_name].append(outcome)
    
    # Show details for most common pattern
    if by_pattern:
        # most_common = max(by_pattern.items(), key=lambda x: len(x[1]))
        most_common = (pattern_name_focus, by_pattern[pattern_name_focus])
        pattern_name, outcomes = most_common
        
        print(f"\nDetailed analysis of '{pattern_name}' ({len(outcomes)} occurrences):")
        print(f"{'Date':<12} {'Price':<10} {'Conf':<8} {'7d_Price':<12} {'7d_Bullish':<12} {'Return':<10}")
        print("-" * 64)
        
        for i, outcome in enumerate(outcomes[:10]):  # Show first 10
            ret = ((outcome.price_7d - outcome.pattern_price) / outcome.pattern_price * 100) \
                  if not np.isnan(outcome.price_7d) else np.nan
            print(f"{outcome.pattern_date:<12} {outcome.pattern_price:<9.2f} "
                  f"{outcome.confidence:<8.2f} {outcome.price_7d:<11.2f} "
                  f"{str(outcome.bullish_7d):<12} {ret:>9.2f}%")
    
    return result


# =========================
# MAIN: Run Examples
# =========================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CANDLESTICK PATTERN EFFICIENCY ANALYSIS - EXAMPLES")
    print("="*70)
    
    # Uncomment examples to run
    
    # example_single_stock()
    # example_high_quality_patterns()
    # example_threshold_tuning()
    # example_multi_stock()
    # example_time_decay()
    # example_focused_patterns()
    # example_custom_detection()
    # example_detailed_outcomes()
    
    print("\n✓ All examples defined. Uncomment in main() to run.")