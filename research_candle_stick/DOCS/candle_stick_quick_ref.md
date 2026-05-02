# Pattern Efficiency Analysis - Quick Reference

## One-Liners

### Basic analysis
```python
result = analyze_candlestick_patterns(df, detect_candles_claude, "AAPL")
```

### Multi-stock
```python
result = analyze_multiple_stocks({"AAPL": df1, "MSFT": df2}, detect_candles_claude)
```

### High-confidence patterns only
```python
result = analyze_candlestick_patterns(df, detect_candles_claude, min_conf_threshold=0.7)
```

### Reversal patterns only
```python
result = analyze_candlestick_patterns(
    df, detect_candles_claude, 
    focus_patterns=["hammer", "hanging_man", "morning_star", "evening_star"]
)
```

### Get stats as DataFrame
```python
df_stats = pattern_stats_to_dataframe(result)
```

### Filter high-quality patterns
```python
df_quality = filter_patterns_by_criteria(result, min_bullish_rate=0.55, min_win_rate=0.55)
```

---

## Common Workflows

### Find Best Patterns for Day Trading (1-3 days)

```python
result = analyze_candlestick_patterns(
    df,
    detect_candles_claude,
    day_gaps=[1, 2, 3],
    min_conf_threshold=0.6,
    min_price_change_pct=0.5,  # Need 0.5% move
)

best = filter_patterns_by_criteria(
    result,
    min_bullish_rate=0.55,
    min_win_rate=0.55,
    min_count=15,
    gap_days=2
)

print(best[["Pattern", "Count", "WinRate", "AvgReturn"]])
```

### Find Swing Trading Patterns (1-4 weeks)

```python
result = analyze_candlestick_patterns(
    df,
    detect_candles_claude,
    day_gaps=[5, 10, 20],
    min_conf_threshold=0.5,
    min_price_change_pct=1.0,
)

best = filter_patterns_by_criteria(
    result,
    min_bullish_rate=0.53,
    min_win_rate=0.52,
    min_count=10,
    gap_days=10
)

print(best)
```

### Cross-Validate Across Markets

```python
stocks = {"AAPL": df_aapl, "MSFT": df_msft, "GOOGL": df_googl}

result = analyze_multiple_stocks(stocks, detect_candles_claude)

# Only patterns in 2+ stocks
for pattern, stats in result["consensus_patterns"].items():
    if stats["stock_consistency"] >= 0.67:
        print(f"{pattern}: {stats['aggregated_bullish_rate_7d']:.1%} bullish")
```

### Optimize Confidence Threshold

```python
thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]

for t in thresholds:
    result = analyze_candlestick_patterns(df, detect_candles_claude, min_conf_threshold=t)
    quality = filter_patterns_by_criteria(result, min_bullish_rate=0.55, min_win_rate=0.5)
    print(f"Threshold {t}: {len(quality)} high-quality patterns")
```

### Custom Pattern Detection

```python
def my_detect(df):
    return detect_candles_claude(
        df,
        DOJI_THRESHOLD=0.1,
        HAMMER_LOWER_WICK_RATIO=3.0
    )

result = analyze_candlestick_patterns(df, my_detect)
```

---

## Key Metrics at a Glance

| Metric | Meaning | Good Value | How to Use |
|--------|---------|-----------|-----------|
| `bullish_rate_7d` | % patterns followed by bullish move | >0.55 (55%) | Filter patterns; >60% is excellent |
| `avg_return_7d` | Average % return in 7 days | >0.5% | Shows profit potential |
| `win_rate_7d` | % of profitable trades | >0.52 | Must be >50% to trade |
| `expected_value_7d` | avg_return × win_rate | >0.30% | Rough profit expectation |
| `sharpe_proxy_7d` | return / volatility | >0.3 | Smooth, consistent profits |
| `total_occurrences` | How many times pattern appeared | >10 | Need enough data |
| `stock_consistency` | % of stocks showing pattern | >0.5 | Reliable across markets |

---

## Parameter Tuning Guide

### For Volatile Markets (Crypto, Small Caps)
```python
result = analyze_candlestick_patterns(
    df,
    detect_func=lambda x: detect_candles_claude(
        x,
        DOJI_THRESHOLD=0.15,
        HAMMER_LOWER_WICK_RATIO=2.0,
        ENGULFING_BODY_MULTIPLIER=1.05
    ),
    min_price_change_pct=0.5,  # Lower threshold
)
```

### For Stable Markets (Blue Chips)
```python
result = analyze_candlestick_patterns(
    df,
    detect_func=lambda x: detect_candles_claude(
        x,
        DOJI_THRESHOLD=0.05,
        HAMMER_LOWER_WICK_RATIO=3.5,
        ENGULFING_BODY_MULTIPLIER=1.3
    ),
    min_price_change_pct=1.5,  # Higher threshold
)
```

### For Aggressive Trading (Max Signals)
```python
result = analyze_candlestick_patterns(
    df,
    min_conf_threshold=0.0,           # Accept all confidence
    min_price_change_pct=0.1,         # Tiny moves count
    use_valid_only=False,             # All patterns
)
```

### For Conservative Trading (High Confidence)
```python
result = analyze_candlestick_patterns(
    df,
    min_conf_threshold=0.75,          # High confidence only
    min_price_change_pct=2.0,         # Large moves
    use_valid_only=True,              # Context-validated patterns
)
```

---

## Output Interpretation

### Reading Pattern Statistics

```
Pattern: hammer (bullish)
Count: 23
Bullish_7d: 65.2%           ← 65% of hammers predicted 7-day up moves
AvgRet_7d: 1.34%            ← Average +1.34% return
WinRate_7d: 61.0%           ← 61% of trades were profitable
ExpVal_7d: 0.82%            ← Expected profit per trade
```

**How to use:**
- **Win rate < 50%**: Skip this pattern (loses money on average)
- **Win rate 50-55%**: Possible but risky
- **Win rate 55-60%**: Good, worth trading
- **Win rate 60%+**: Excellent, strong edge

### Reading Aggregate Stats (Multi-Stock)

```
Pattern: hammer_bullish
TotalOccurrences: 127           ← 127 times across all stocks
StockConsistency: 75.0%         ← Appeared in 75% of stocks
AvgBullishRate_7d: 58.3%        ← Average 58% bullish across stocks
AvgWinRate: 54.2%               ← Average 54% win rate
```

**How to use:**
- **Stock consistency > 75%**: Reliable across different assets
- **BullishRate > 60%**: Strong predictive power
- **> 100 total occurrences**: Statistically significant

---

## Troubleshooting

### "No patterns detected"
```python
# Check 1: Looser detection threshold
result = analyze_candlestick_patterns(
    df,
    detect_func=lambda x: detect_candles_claude(
        x,
        DOJI_THRESHOLD=0.20,          # Much looser
        LONG_DAY_THRESHOLD=0.60       # Easier to trigger
    ),
)

# Check 2: Use all patterns, not just valid ones
result = analyze_candlestick_patterns(
    df,
    detect_candles_claude,
    use_valid_only=False              # Include all detected patterns
)
```

### "Very high bullish rates (>80%)"
```python
# This might be overfitting. Try:
# - Longer time horizon (30-day instead of 7-day)
# - Stricter confidence threshold
# - More data (longer date range)
# - Validate on out-of-sample data
```

### "Low win rates across all patterns"
```python
# Try:
# - Adjust min_price_change_pct to realistic levels
# - Look at longer time horizons (14d/30d instead of 7d)
# - Focus on high-confidence patterns only
# - Check that your price data is correct
```

### "Too many patterns, hard to trade"
```python
# Filter results
high_quality = filter_patterns_by_criteria(
    result,
    min_bullish_rate=0.60,       # Very selective
    min_win_rate=0.60,
    min_count=20,                 # Many occurrences
    gap_days=7
)

# Or focus on specific patterns
result = analyze_candlestick_patterns(
    df,
    detect_candles_claude,
    focus_patterns=["hammer", "morning_star", "shooting_star"]  # Reversals only
)
```

---

## Analysis Checklist

- [ ] Loaded OHLC data correctly (columns: open, high, low, close)
- [ ] Ran `analyze_candlestick_patterns()` with appropriate parameters
- [ ] Checked pattern counts (need >10 for statistical significance)
- [ ] Verified win rates are >50% (or >55% for trading)
- [ ] Looked at Sharpe proxy (volatility-adjusted returns)
- [ ] Cross-validated with multiple stocks if possible
- [ ] Tested multiple time horizons (7d/14d/30d)
- [ ] Filtered out low-confidence patterns
- [ ] Reviewed actual outcomes for top patterns

---

## Performance Expectations

| Market Type | Expected Win Rate | Expected Return |
|-------------|-------------------|-----------------|
| Random baseline | 50% | 0% |
| Weak pattern | 51-53% | 0-0.2% per trade |
| Decent pattern | 54-57% | 0.2-0.5% per trade |
| Strong pattern | 58-62% | 0.5-1.0% per trade |
| Excellent pattern | 63%+ | 1.0%+ per trade |

*Note: Returns diminish with more data and longer backtests*