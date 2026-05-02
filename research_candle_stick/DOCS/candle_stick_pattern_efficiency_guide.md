# Candlestick Pattern Efficiency Analysis - Complete Guide

## Overview

This framework analyzes how well candlestick patterns predict future price movements. It computes:

1. **Prediction Probabilities**: What % of patterns lead to bullish/bearish moves in 7/14/30 days
2. **Price Outcomes**: Expected return given a pattern at different time horizons
3. **Win Rates**: How often a pattern's direction matches actual price movement
4. **Risk Metrics**: Sharpe ratio proxy, expected value, consistency across stocks

---

## Part 1: Single Stock Analysis

### Basic Usage

```python
from pattern_efficiency_analysis import analyze_candlestick_patterns
from detect_candles_refactored import detect_candles_claude

# Load your OHLC data
df = pd.read_csv("historical_data.csv", index_col="date")
# Expected columns: open, high, low, close

# Analyze patterns
result = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL"
)

# View results
print(f"Detected {result.n_patterns_detected} patterns in {result.n_candles} candles")
print(f"Date range: {result.date_range}")
```

### View Pattern Statistics

```python
from pattern_efficiency_analysis import pattern_stats_to_dataframe

# Convert to readable format
stats_df = pattern_stats_to_dataframe(result)
print(stats_df.to_string())

# Output columns:
# Pattern: Pattern name and direction (e.g., "hammer_bullish")
# Count: Total occurrences
# HighConf: Count above confidence threshold
# Bullish_7d: % of patterns followed by bullish move in 7 days
# AvgRet_7d: Average return % after 7 days
# WinRate_7d: % of trades that would be profitable
# ExpVal_7d: Expected value (avg return × win rate)
```

### Filtered Results

```python
from pattern_efficiency_analysis import filter_patterns_by_criteria

# Get only high-quality patterns (55%+ bullish rate, 50%+ win rate)
high_quality = filter_patterns_by_criteria(
    result,
    min_bullish_rate=0.55,  # 55% bullish rate
    min_win_rate=0.50,       # 50% profitable trades
    min_count=10,            # At least 10 occurrences
    gap_days=7               # Look at 7-day predictions
)

print(high_quality)
```

### Access Raw Outcomes

```python
# Get detailed outcome data for each pattern
outcomes = result.outcomes  # List[PatternOutcome]

for outcome in outcomes[:5]:
    print(f"{outcome.pattern_name} ({outcome.direction}) @ {outcome.pattern_date}")
    print(f"  Confidence: {outcome.confidence:.2f}")
    print(f"  Price: ${outcome.pattern_price:.2f}")
    print(f"  7d price: ${outcome.price_7d:.2f} (bullish: {outcome.bullish_7d})")
    print()
```

---

## Part 2: Tuning Parameters

### Confidence Threshold

Control how strict pattern detection is:

```python
# Only use high-confidence patterns
result_strict = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    min_conf_threshold=0.70  # Only patterns with 70%+ confidence
)

# Include lower confidence patterns for more data
result_loose = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    min_conf_threshold=0.30  # Include patterns with 30%+ confidence
)
```

### Pattern Selection

Analyze only specific patterns:

```python
# Focus on reversal patterns only
result = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    focus_patterns=["hammer", "hanging_man", "shooting_star", "morning_star", "evening_star"]
)
```

### Bullish/Bearish Classification

Adjust what counts as "bullish" movement:

```python
# Stricter: require 2% move to call it bullish
result_strict = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    min_price_change_pct=2.0  # 2% threshold
)

# Looser: any positive move counts as bullish
result_loose = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    min_price_change_pct=0.0  # Any positive return
)
```

### Time Horizons

Analyze different forward-looking periods:

```python
# Short-term trading (1, 3, 5 days)
result_short = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    day_gaps=[1, 3, 5]
)

# Medium-term (2, 4, 8 weeks)
result_medium = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    day_gaps=[14, 28, 56]
)
```

### Valid Patterns Only

```python
# Use only patterns that passed trend/support/resistance validation
result_valid = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    use_valid_only=True  # Use *_valid patterns + *_valid_conf
)

# Include all detected patterns regardless of context
result_all = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    use_valid_only=False  # Use all *_conf columns
)
```

### Custom Detection Function

```python
# Use with custom thresholds
from detect_candles_refactored import detect_candles_claude

def detect_with_custom_thresholds(df):
    return detect_candles_claude(
        df,
        DOJI_THRESHOLD=0.15,
        HAMMER_LOWER_WICK_RATIO=2.0,
        ENGULFING_BODY_MULTIPLIER=1.05
    )

result = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_with_custom_thresholds,
    stock_name="AAPL"
)
```

---

## Part 3: Multi-Stock Analysis

### Basic Setup

```python
from pattern_efficiency_analysis import analyze_multiple_stocks

# Prepare data for multiple stocks
stock_data = {
    "AAPL": pd.read_csv("aapl.csv", index_col="date"),
    "MSFT": pd.read_csv("msft.csv", index_col="date"),
    "GOOGL": pd.read_csv("googl.csv", index_col="date"),
}

# Analyze all stocks
multi_result = analyze_multiple_stocks(
    stock_dataframes=stock_data,
    detect_func=detect_candles_claude,
    day_gaps=[7, 14, 30]
)
```

### Access Results

```python
# Individual stock results
individual_results = multi_result["individual_results"]
for result in individual_results:
    print(f"{result.stock_name}: {result.n_patterns_detected} patterns")

# Aggregated statistics across all stocks
aggregate_stats = multi_result["aggregate_stats"]
for pattern_key, stats in aggregate_stats.items():
    print(f"{pattern_key}:")
    print(f"  Total occurrences across all stocks: {stats['total_occurrences']}")
    print(f"  Stock consistency: {stats['stock_consistency']:.1%}")
    print(f"  Avg bullish rate (7d): {stats['aggregated_bullish_rate_7d']:.1%}")

# High-confidence patterns appearing in multiple stocks
consensus_patterns = multi_result["consensus_patterns"]
for pattern_key, stats in consensus_patterns.items():
    print(f"✓ {pattern_key} (appears in {stats['stock_consistency']:.1%} of stocks)")
```

### Multi-Stock Aggregation Methods

```python
# Weighted by pattern count (default)
result_weighted = analyze_multiple_stocks(
    stock_dataframes=stock_data,
    detect_func=detect_candles_claude,
    aggregation_method="weighted"  # Stocks with more patterns have more influence
)

# Simple average across stocks
result_simple = analyze_multiple_stocks(
    stock_dataframes=stock_data,
    detect_func=detect_candles_claude,
    aggregation_method="simple"  # Each stock counts equally
)

# Median (robust to outliers)
result_median = analyze_multiple_stocks(
    stock_dataframes=stock_data,
    detect_func=detect_candles_claude,
    aggregation_method="median"
)
```

### Consistency Filtering

```python
# Only patterns that appear in 50%+ of stocks
result = analyze_multiple_stocks(
    stock_dataframes=stock_data,
    detect_func=detect_candles_claude,
    min_pattern_count=5,  # Min 5 occurrences per stock
    # Consensus patterns automatically filtered to 50%+ stock consistency
)

# Stricter: only patterns in 75%+ of stocks
consensus = {
    k: v for k, v in result["consensus_patterns"].items()
    if v["stock_consistency"] >= 0.75
}
```

---

## Part 4: Interpretation & Metrics

### Key Metrics Explained

#### Bullish Rate (e.g., `bullish_rate_7d`)
- **What it is**: % of times a pattern was followed by a bullish move within 7 days
- **Range**: 0.0 (never bullish) to 1.0 (always bullish)
- **How to use**: Compare to baseline (50% = random). >55% is interesting, >60% is strong
- **Example**: `bullish_rate_7d=0.65` → 65% of hammers were followed by bullish moves

#### Average Return (e.g., `avg_return_7d`)
- **What it is**: Average price change % within 7 days of the pattern
- **Range**: Any positive or negative value
- **How to use**: Look for positive values. -1% means average loss
- **Example**: `avg_return_7d=1.2` → On average, +1.2% within 7 days

#### Win Rate (e.g., `win_rate_7d`)
- **What it is**: % of patterns where the direction prediction was correct
- **Range**: 0.0 to 1.0
- **How to use**: Baseline is 50%. >50% means predictive power. >55% is useful
- **Example**: `win_rate_7d=0.58` → 58% of trades would be profitable

#### Expected Value (e.g., `expected_value_7d`)
- **What it is**: Average return × win rate (rough estimate of expected profit)
- **Range**: Negative (losing pattern) to positive (profitable)
- **How to use**: Higher is better. Positive expected value = profitable pattern
- **Formula**: `avg_return_7d × win_rate_7d`
- **Example**: `1.2% × 0.58 = 0.696%` expected value per pattern

#### Sharpe Proxy (e.g., `sharpe_proxy_7d`)
- **What it is**: Average return / standard deviation of returns
- **Range**: Positive (smooth, low volatility) to negative (volatile, unpredictable)
- **How to use**: Higher = more consistent returns with less volatility
- **Example**: `sharpe_proxy_7d=0.5` → Returns average 0.5 std deviations above zero

#### Stock Consistency
- **What it is**: % of stocks showing this pattern
- **Range**: 0.0 (no stocks) to 1.0 (all stocks)
- **How to use**: Higher = more reliable across different assets
- **Example**: 0.75 = pattern appears in 75% of your stock list

---

## Part 5: Advanced Analysis Examples

### Example 1: Find Best Patterns for Short-Term Trading

```python
# Analyze with short-term focus
result = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    day_gaps=[1, 3, 5],  # 1, 3, 5-day horizons
    min_conf_threshold=0.70,
    min_price_change_pct=0.5,  # Need 0.5%+ move to count
)

# Filter for profitable patterns
profitable = filter_patterns_by_criteria(
    result,
    min_bullish_rate=0.55,
    min_win_rate=0.55,
    min_count=20,
    gap_days=3
)

print("Best patterns for 3-day trades:")
print(profitable)
```

### Example 2: Cross-Market Pattern Validation

```python
# Analyze multiple sectors
stock_data = {
    "AAPL": df_aapl,   # Tech
    "JPM": df_jpm,     # Finance
    "JNJ": df_jnj,     # Healthcare
    "XOM": df_xom,     # Energy
}

result = analyze_multiple_stocks(
    stock_dataframes=stock_data,
    detect_func=detect_candles_claude,
    min_pattern_count=10,
)

# Patterns that work across sectors
universal_patterns = {
    k: v for k, v in result["consensus_patterns"].items()
    if v["stock_consistency"] >= 0.75  # 75% of sectors
}

print("Universal patterns:")
for pattern, stats in universal_patterns.items():
    print(f"{pattern}: {stats['aggregated_bullish_rate_7d']:.1%} bullish rate")
```

### Example 3: Time Decay Analysis

```python
# How predictive power changes over time
result = analyze_candlestick_patterns(
    df=df,
    detect_func=detect_candles_claude,
    stock_name="AAPL",
    day_gaps=[1, 7, 14, 30, 60]  # Different time horizons
)

# Compare predictive power
for pattern, stat in result.pattern_stats.items():
    print(f"{pattern}:")
    print(f"  1d: {stat.bullish_rate_7d:.1%}" if hasattr(stat, 'bullish_rate_1d') else "")
    print(f"  7d: {stat.bullish_rate_7d:.1%}")
    print(f"  14d: {stat.bullish_rate_14d:.1%}")
    print(f"  30d: {stat.bullish_rate_30d:.1%}")
```

### Example 4: Confidence Threshold Optimization

```python
# Test different confidence thresholds
thresholds = [0.0, 0.3, 0.5, 0.7, 0.9]
results = {}

for threshold in thresholds:
    result = analyze_candlestick_patterns(
        df=df,
        detect_func=detect_candles_claude,
        stock_name="AAPL",
        min_conf_threshold=threshold
    )
    
    # Count high-quality patterns
    high_quality = filter_patterns_by_criteria(
        result,
        min_bullish_rate=0.55,
        min_win_rate=0.50,
        min_count=5
    )
    
    results[threshold] = {
        "n_patterns": result.n_patterns_detected,
        "n_quality": len(high_quality),
        "quality_pct": len(high_quality) / max(1, len(result.pattern_stats))
    }

# Find optimal threshold
optimal = max(results.items(), key=lambda x: x[1]["quality_pct"])
print(f"Optimal confidence threshold: {optimal[0]}")
```

---

## Output Structures

### StockAnalysisResult

```python
result = StockAnalysisResult(
    stock_name="AAPL",
    n_candles=1000,
    n_patterns_detected=47,
    date_range=("2023-01-01", "2024-01-01"),
    pattern_stats={
        "hammer_bullish": PatternStats(...),
        "bullish_engulfing_bullish": PatternStats(...),
        # ... more patterns
    },
    outcomes=[
        PatternOutcome(...),
        PatternOutcome(...),
        # ... detailed outcome for each pattern
    ],
    overall_bullish_rate_7d=0.55,
    overall_bullish_rate_14d=0.52,
    overall_bullish_rate_30d=0.48,
)
```

### PatternStats (inside result.pattern_stats)

```python
stat = PatternStats(
    pattern_name="hammer",
    direction="bullish",
    total_occurrences=15,
    high_conf_count=12,
    
    # Bullish rates at different horizons
    bullish_rate_7d=0.67,
    bullish_rate_14d=0.60,
    bullish_rate_30d=0.53,
    
    # Average returns at different horizons
    avg_return_7d=1.23,      # 1.23% average return
    avg_return_14d=2.05,
    avg_return_30d=3.12,
    
    # Win rates (% profitable)
    win_rate_7d=0.60,
    win_rate_14d=0.60,
    win_rate_30d=0.67,
    
    # Expected value (return × win rate)
    expected_value_7d=0.738,   # 0.738% expected profit
    expected_value_14d=1.23,
    expected_value_30d=2.09,
    
    # Sharpe ratio proxy
    sharpe_proxy_7d=0.45,
    sharpe_proxy_14d=0.52,
    sharpe_proxy_30d=0.61,
)
```

### PatternOutcome (raw data)

```python
outcome = PatternOutcome(
    pattern_name="hammer",
    direction="bullish",
    pattern_price=150.23,      # Price when pattern occurred
    pattern_date="2023-06-15",
    confidence=0.82,           # Pattern confidence score
    
    # Prices at future dates
    price_7d=152.18,
    price_14d=153.50,
    price_30d=155.75,
    
    # Whether each move was bullish
    bullish_7d=True,           # Price went up
    bullish_14d=True,
    bullish_30d=True,
)
```

---

## Function Signatures

### analyze_candlestick_patterns

```python
def analyze_candlestick_patterns(
    df: pd.DataFrame,
    detect_func,
    stock_name: str = "Stock",
    day_gaps: List[int] = [7, 14, 30],
    min_conf_threshold: float = 0.0,
    min_price_change_pct: float = 0.01,  # 1%
    use_valid_only: bool = True,
    focus_patterns: Optional[List[str]] = None,
    calculate_sharpe: bool = True,
    debug: bool = False
) -> StockAnalysisResult
```

### analyze_multiple_stocks

```python
def analyze_multiple_stocks(
    stock_dataframes: Dict[str, pd.DataFrame],
    detect_func,
    day_gaps: List[int] = [7, 14, 30],
    min_conf_threshold: float = 0.0,
    min_price_change_pct: float = 0.01,
    use_valid_only: bool = True,
    focus_patterns: Optional[List[str]] = None,
    calculate_sharpe: bool = True,
    aggregation_method: str = "weighted",
    min_pattern_count: int = 5,
    debug: bool = False
) -> Dict
```

---

## Tips & Best Practices

1. **Start conservative**: Begin with `min_conf_threshold=0.5` to focus on high-quality patterns
2. **Test multiple timeframes**: Patterns may predict 7-day moves but not 30-day moves
3. **Cross-validate**: Use `analyze_multiple_stocks` to verify patterns work across different assets
4. **Watch for survivorship bias**: More data = more reliable statistics
5. **Consider market conditions**: Patterns may work better in trends vs ranges
6. **Filter by win rate**: Patterns with <55% win rate rarely generate alpha
7. **Look at Sharpe proxy**: High expected value with high volatility is risky














