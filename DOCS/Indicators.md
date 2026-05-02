# 📊 Technical Indicators Library

A comprehensive guide to **primary and advanced technical indicators** with intuitive explanations, mathematical derivations, chart interpretations, and practical trading applications.

**Table of Contents:**
- [Primary Indicators](#-primary-indicators)
  - [Moving Averages](#1-moving-averages-sma--ema)
  - [RSI](#2-rsi-relative-strength-index)
  - [MACD](#3-macd-moving-average-convergence-divergence)
  - [ATR](#4-atr-average-true-range)
  - [Bollinger Bands](#5-bollinger-bands)
  - [OBV](#6-obv-on-balance-volume)
  - [VWAP](#7-vwap-volume-weighted-average-price)
  - [Stochastic](#8-stochastic-oscillator)
- [Advanced Indicators](#-advanced-indicators)
  - [Ichimoku Cloud](#1-ichimoku-cloud)
  - [Supertrend](#2-supertrend)
  - [CCI](#3-cci-commodity-channel-index)
  - [Donchian Channel](#4-donchian-channel)
  - [Keltner Channel](#5-keltner-channel)
  - [Hull MA](#6-hma-hull-moving-average)
  - [KAMA](#7-kama-kaufman-adaptive-moving-average)
- [Core Concepts](#-core-mathematical-concepts)
- [Practical Applications](#-practical-applications)

---

# 🟢 PRIMARY INDICATORS

Core indicators used in virtually all trading systems. These form the foundation of technical analysis.

---

## 1. Moving Averages (SMA / EMA)

**Category:** Trend | **Type:** Foundational | **Timeframe:** Any | **Best Used:** Trend identification

### 🎯 Intuition

Moving averages **smooth noisy price data** into a clean trend line. Think of it as a filter that removes "market noise" and reveals the underlying trend direction.

- **SMA (Simple MA):** Equal weight to all prices in the period
- **EMA (Exponential MA):** Recent prices weighted more heavily (faster response)

### 📐 Mathematical Definition

**Simple Moving Average (SMA):**
```
SMA(t, n) = (P(t) + P(t-1) + ... + P(t-n+1)) / n
         = (1/n) × Σ(P(t-i)) for i = 0 to n-1
```

**Exponential Moving Average (EMA):**
```
EMA(t) = α × P(t) + (1-α) × EMA(t-1)

where α (alpha) = 2 / (n + 1)

Example for EMA-20:
α = 2 / (20 + 1) = 0.0952 (9.52% weight to current price)
```

**Why exponential?**
- SMA gives equal weight: [1/n, 1/n, ..., 1/n]
- EMA gives exponential decay: [α, α(1-α), α(1-α)², ...]
- Older prices get progressively less weight

### 📊 Chart Interpretation

```
Price Chart with SMA-20 (blue) and EMA-20 (red):

     ╱╲       ╱╲
    ╱  ╲ ╱╲  ╱  ╲
   ╱    ╲╱  ╲╱    ╲ ← Price (volatile)
  ╱─────────────────╲ ← SMA-20 (smoother, laggier)
 ╱───────────────────╲ ← EMA-20 (responds faster)

Key Patterns:
┌─────────────────────────────────────────────────┐
│ PATTERN              │ INTERPRETATION             │
├─────────────────────────────────────────────────┤
│ Price > SMA          │ Uptrend (bearish = sell)   │
│ Price < SMA          │ Downtrend (bullish = buy)  │
│ SMA slopes up        │ Trend strengthening        │
│ SMA slopes down      │ Trend weakening            │
│ EMA crosses SMA up   │ Bullish momentum shift      │
│ Price bounces off MA │ Support/resistance test    │
└─────────────────────────────────────────────────┘
```

### 💡 Practical Examples

**Example 1: Trend Confirmation**
```python
import pandas as pd
import numpy as np

# Calculate moving averages
df['SMA_20'] = df['close'].rolling(20).mean()
df['EMA_20'] = df['close'].ewm(span=20).mean()
df['EMA_50'] = df['close'].ewm(span=50).mean()

# Trend detection
df['is_uptrend'] = df['close'] > df['SMA_20']
df['is_downtrend'] = df['close'] < df['SMA_20']

# Golden Cross: EMA-20 crosses above EMA-50 (bullish signal)
df['golden_cross'] = (df['EMA_20'] > df['EMA_50']) & \
                     (df['EMA_20'].shift(1) <= df['EMA_50'].shift(1))

# Death Cross: EMA-20 crosses below EMA-50 (bearish signal)
df['death_cross'] = (df['EMA_20'] < df['EMA_50']) & \
                    (df['EMA_20'].shift(1) >= df['EMA_50'].shift(1))
```

**Example 2: Dynamic Support/Resistance**
```python
# Price bouncing off MA indicates strong trend
df['price_near_ma'] = abs(df['close'] - df['EMA_20']) / df['close'] < 0.01
df['bounce_signal'] = (df['close'] > df['EMA_20'].shift(1)) & \
                      (df['low'] <= df['EMA_20']) & \
                      (df['close'] > df['open'])  # Green candle bounce
```

### ⚙️ Parameters

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| **Period (n)** | 20 | 5-200 | Shorter = faster response, more whipsaws; Longer = smoother, more lag |
| **Type** | EMA | SMA/EMA | EMA responds faster but may be whippy; SMA is stable but sluggish |

### ✅ Best Practices

1. **Use EMA for trending markets** — faster entry signals
2. **Use SMA for establishing support/resistance** — cleaner zones
3. **Combine fast + slow MA** — 20/50, 20/200, 50/200 for crossover strategies
4. **Avoid in choppy markets** — too many false signals
5. **Pair with volume confirmation** — ensure trend has conviction

---

## 2. RSI (Relative Strength Index)

**Category:** Momentum | **Type:** Oscillator | **Timeframe:** 5m-Daily | **Best Used:** Overbought/Oversold detection

### 🎯 Intuition

RSI measures **how fast and far price has moved recently**. It answers: *"Are buyers or sellers in control right now?"*

A high RSI (above 70) means **buying momentum is extreme** → market may reverse down soon.
A low RSI (below 30) means **selling pressure is extreme** → market may reverse up soon.

Think of it as a **speedometer for momentum** — not where the price is, but *how fast* it got there.

### 📐 Mathematical Definition

```
Step 1: Calculate average gains and losses over period (typically 14 bars)
Avg_Gain = (sum of positive changes) / 14
Avg_Loss = (sum of negative changes) / 14

Step 2: Calculate Relative Strength
RS = Avg_Gain / Avg_Loss

Step 3: Normalize to 0-100 range
RSI = 100 - (100 / (1 + RS))

Simplified:
RSI = 100 × (Avg_Gain / (Avg_Gain + Avg_Loss))
```

**Example Calculation:**
```
Prices: 100, 102, 101, 103, 104, 102, 105, 104, 106, 105

Changes: +2, -1, +2, +1, -2, +3, -1, +2, -1

Gains (positive only): 2, 2, 1, 3, 2 → Sum = 10
Losses (absolute value): 1, 2, 1, 1 → Sum = 5

Avg_Gain = 10 / 14 ≈ 0.71
Avg_Loss = 5 / 14 ≈ 0.36
RS = 0.71 / 0.36 = 1.98
RSI = 100 - (100 / (1 + 1.98)) = 100 - 33.4 = 66.6
```

### 📊 Chart Interpretation

```
RSI Line on a Chart:
100 ┌─────────────────────────────┐ (Overbought limit)
    │        /╲    /╲    /╲       │
 80 │       ╱  ╲  ╱  ╲  ╱  ╲      │
    │      ╱    ╲╱    ╲╱    ╲     │
 70 |━━━━━━━━━━━━━━━━━━━━━━━━━━━━| Overbought threshold
    │    ╱                    ╲   │
 50 |─────────────────────────────| Neutral (no bias)
    │   ╱                      ╲  │
 30 |━━━━━━━━━━━━━━━━━━━━━━━━━━━━| Oversold threshold
    │  ╱  ╲    ╱╲    ╱╲    ╱╲     │
 20 │ ╱    ╲  ╱  ╲  ╱  ╲  ╱  ╲    │
    │╱      ╲╱    ╲╱    ╲╱    ╲   │
  0 └─────────────────────────────┘ (Oversold limit)

Key Zones:
┌──────────────┬─────────┬──────────────────────┐
│ RSI Range    │ Signal  │ Meaning              │
├──────────────┼─────────┼──────────────────────┤
│ 70-100       │ OB      │ Overbought (too hot) │
│ 50-70        │ Strong  │ Strong uptrend       │
│ 30-50        │ Weak    │ Weak uptrend         │
│ 0-30         │ OS      │ Oversold (too cold)  │
└──────────────┴─────────┴──────────────────────┘
```

### 🔄 Divergence Trading (Advanced)

RSI is most powerful in **divergence** patterns:

```
Bullish Divergence (Reversal signal):
- Price makes lower low
- RSI makes higher low
- Suggests selling pressure weakening despite lower price

    Price: ╱╲      ╱╲      ╱╲ ← Lower lows
          ╱  ╲    ╱  ╲    ╱
         ╱    ╲  ╱    ╲  ╱

    RSI:   ╱╲      ╱╲      ╱╲ ← Higher lows (divergence!)
          ╱  ╲    ╱  ╲    ╱
         ╱    ╲  ╱    ╲  ╱

Signal: Bullish → expect reversal up soon
```

### 💡 Practical Usage

```python
# Calculate RSI-14
def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = pd.Series(gains).rolling(period).mean()
    avg_loss = pd.Series(losses).rolling(period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

df['rsi'] = calculate_rsi(df['close'].values)

# Trading signals
df['overbought'] = df['rsi'] > 70
df['oversold'] = df['rsi'] < 30

# Divergence detection
df['price_lower_low'] = (df['low'] < df['low'].shift(1)) & \
                         (df['low'].shift(1) < df['low'].shift(2))
df['rsi_higher_low'] = (df['rsi'] > df['rsi'].shift(1)) & \
                        (df['rsi'].shift(1) < df['rsi'].shift(2))
df['bullish_divergence'] = df['price_lower_low'] & df['rsi_higher_low']
```

### ⚙️ Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| **Period** | 14 | Standard; 5-21 for faster, 21-28 for slower response |
| **Overbought** | 70 | Can adjust to 60-80 depending on volatility |
| **Oversold** | 30 | Can adjust to 20-40 depending on volatility |

### ⚠️ Common Pitfalls

- **Don't fade RSI > 70 in strong uptrends** — strong trends can sustain high RSI
- **RSI ≠ reversal guarantee** — use with support/resistance, not alone
- **Adjust thresholds for different assets** — crypto often stays overbought longer

---

## 3. MACD (Moving Average Convergence Divergence)

**Category:** Trend + Momentum | **Type:** Composite | **Timeframe:** 4h-Daily | **Best Used:** Trend identification + momentum shifts

### 🎯 Intuition

MACD measures the **relationship between two moving averages** (fast vs slow). 

- When they're **far apart** → strong trend, high momentum
- When they **converge** → trend weakening
- When **MACD crosses its signal line** → trend shift confirmed

Think of it as a **momentum meter** that also shows trend strength.

### 📐 Mathematical Definition

```
Step 1: Calculate fast and slow EMAs
EMA_12 = 12-period exponential moving average
EMA_26 = 26-period exponential moving average

Step 2: Calculate MACD line
MACD = EMA_12 - EMA_26

Step 3: Calculate Signal line (smoothed MACD)
Signal_Line = EMA_9(MACD)

Step 4: Calculate Histogram
Histogram = MACD - Signal_Line

Interpretation of Each Component:
├─ MACD line: Shows momentum direction
├─ Signal line: Confirms momentum shift (EMA smoothing)
└─ Histogram: Visualizes momentum strength and reversal
```

**Why these specific periods (12, 26, 9)?**
- 12 + 26 = 38 periods total lookback (reasonable for trend)
- 9 = roughly half of 12 (provides clean signal smoothing)
- Based on traders' preferences over decades (become standard)

### 📊 Chart Interpretation

```
Price + MACD Chart:

Price:      ╱╲╲╱╲
           ╱  ╲╲╱  ╲╱
MACD:     /    \
Signal:  /──────\        ← Signal Line
Hist: ▓▓ ░ ░░░░░░ ░░     ← Histogram (bars)

Three Components:

1. MACD Line (thick): Momentum direction
   - Above Signal = momentum up
   - Below Signal = momentum down

2. Signal Line (thin): Confirms shifts
   - MACD crosses above = buy signal
   - MACD crosses below = sell signal

3. Histogram (bars):
   - Growing height = momentum increasing
   - Shrinking height = momentum fading
   - Color change = potential reversal

Key Patterns:
┌────────────────────────────────────────────┐
│ PATTERN                    │ SIGNAL         │
├────────────────────────────────────────────┤
│ MACD > Signal, histogram + │ Strong uptrend │
│ MACD < Signal, histogram - │ Strong dntrend │
│ Histogram shrinking        │ Momentum fade  │
│ Histogram color flip       │ Potential turn │
│ MACD far from Signal       │ High momentum  │
└────────────────────────────────────────────┘
```

### 💡 Practical Usage

```python
# Calculate MACD
def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = pd.Series(prices).ewm(span=fast).mean()
    ema_slow = pd.Series(prices).ewm(span=slow).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

df['macd'], df['signal'], df['histogram'] = calculate_macd(df['close'].values)

# Trading signals
# Signal 1: Crossover (most popular)
df['macd_crosses_above'] = (df['macd'] > df['signal']) & \
                           (df['macd'].shift(1) <= df['signal'].shift(1))
df['macd_crosses_below'] = (df['macd'] < df['signal']) & \
                           (df['macd'].shift(1) >= df['signal'].shift(1))

# Signal 2: Histogram reversal (momentum shift)
df['histogram_turns_positive'] = (df['histogram'] > 0) & \
                                 (df['histogram'].shift(1) <= 0)
df['histogram_turns_negative'] = (df['histogram'] < 0) & \
                                 (df['histogram'].shift(1) >= 0)

# Signal 3: Divergence
df['rsi_higher_low'] = (df['rsi'] > df['rsi'].shift(1))
df['macd_lower_low'] = (df['macd'] < df['macd'].shift(1))
df['bullish_div'] = df['rsi_higher_low'] & df['macd_lower_low']
```

### ⚙️ Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| **Fast EMA** | 12 | Decreasing makes it faster (more signals, more noise) |
| **Slow EMA** | 26 | Increasing makes it slower (fewer signals, smoother) |
| **Signal** | 9 | Higher = more confirmation, fewer false signals |

---

## 4. ATR (Average True Range)

**Category:** Volatility | **Type:** Measurement | **Timeframe:** Any | **Best Used:** Stop loss sizing, position sizing

### 🎯 Intuition

ATR answers: **"How volatile is this market right now?"** (not which direction, just the magnitude of movement)

- High ATR → Market is volatile, wide price swings
- Low ATR → Market is quiet, tight consolidation

This is critical for **risk management**: use wider stops in high ATR, tighter stops in low ATR.

### 📐 Mathematical Definition

```
Step 1: Calculate True Range for each bar
TR = max of:
  a) High - Low  (standard range)
  b) |High - Previous Close|  (gap up)
  c) |Low - Previous Close|   (gap down)

Why include gaps? Without it, you'd underestimate volatility if market gaps past your stop.

Step 2: Average the True Range
ATR = SMA(TR, 14)  or  EMA(TR, 14)

Example:
Date    High  Low   Close  Prev_Close  TR
1       105   100   103    102         5 (high-low)
2       107   101   105    103         6 (high-prev=4, low-prev=2, so TR=max=4)
3       106   95    97     105         11 (prev-low=10, high-low=11, so TR=11)
4       100   93    95     97          7 (high-low=7)

ATR-14 = SMA([5, 6, 11, 7, ...])
```

### 📊 Chart Interpretation

```
Price + ATR Chart:

Price: ╱╲╱╱╲╱╲╱
      ╱  ╲╱  ╲╱  ╲

ATR:  ▁▂▃▄▅ ▁▂▃  ← High ATR (volatile)
      ▂▃▄ ▁▂▃▂▁  ← Low ATR (quiet)

Meanings:
┌────────────────┬──────────────────┐
│ ATR Level      │ Market Condition │
├────────────────┼──────────────────┤
│ Rising ATR     │ Volatility ↑     │
│ Falling ATR    │ Volatility ↓     │
│ High ATR       │ Breakout risk    │
│ Low ATR        │ Squeeze forming  │
└────────────────┴──────────────────┘

Volatility Cycle:
Low ATR → Squeeze → Breakout → High ATR → Consolidation → Low ATR (repeat)
```

### 💡 Practical Usage

```python
# Calculate ATR
def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

# Example 1: Dynamic Stop Loss Sizing
df['stop_loss_distance'] = df['atr'] * 2  # Stop 2× ATR below entry
df['take_profit_distance'] = df['atr'] * 3  # Take profit 3× ATR above entry

# Example 2: Squeeze Detection (low volatility)
df['atr_sma'] = df['atr'].rolling(20).mean()
df['volatility_squeeze'] = df['atr'] < df['atr_sma'] * 0.8  # ATR < 80% of average

# Example 3: Position Sizing
df['position_size'] = 1000 / df['atr']  # Smaller position in high vol, larger in low vol
```

### ⚙️ Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| **Period** | 14 | Standard; 10-20 common |

### ✅ Pro Tips

1. **Use ATR for stop loss** → Stop = Entry - (ATR × multiplier)
2. **Wider stops in choppy markets** → Use 2-3× ATR
3. **Tighter stops in quiet markets** → Use 1.5× ATR
4. **Rising ATR = breakout probable** → Prepare for bigger moves
5. **Falling ATR = range forming** → Look for tightening bands

---

## 5. Bollinger Bands

**Category:** Volatility | **Type:** Dynamic Envelope | **Timeframe:** Any | **Best Used:** Identifying overbought/oversold, breakout confirmation

### 🎯 Intuition

Bollinger Bands create a **dynamic price envelope** around a moving average based on volatility.

- **Squeeze** (bands tight) → Low volatility, breakout coming
- **Expansion** (bands wide) → High volatility, trending hard
- Price bouncing between bands → Normal ranging behavior

Think of it as **elastic bands around price** that expand/contract with volatility.

### 📐 Mathematical Definition

```
Step 1: Calculate middle band (20-period SMA)
Middle = SMA(Close, 20)

Step 2: Calculate standard deviation
σ = Standard_Deviation(Close, 20)

Step 3: Create upper and lower bands
Upper_Band = Middle + (k × σ)
Lower_Band = Middle - (k × σ)

where k = 2 (standard; ranges 1-3)

Standard Deviation: σ = √(Σ(x - mean)² / n)
Measures how far prices deviate from the average

Example with simple data:
Prices: 100, 101, 99, 102, 98
Mean = 100
Deviations: 0, 1, -1, 2, -2
Squared: 0, 1, 1, 4, 4
Variance = 10/5 = 2
σ = √2 ≈ 1.41

If k=2:
Upper = 100 + (2 × 1.41) = 102.82
Lower = 100 - (2 × 1.41) = 97.18
```

### 📊 Chart Interpretation

```
Price Chart with Bollinger Bands:

Upper Band  ╱────────────╲
           ╱              ╲
Middle     ─────────────── ← SMA-20
          ╱                ╲
Lower Band ╲────────────────╱

Three Zones:

Zone 1: Price above Upper Band
  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
  └─ Overbought (potential reversal down)
  └─ Or strong uptrend continuing

Zone 2: Price between bands
  ────────────────────────────
  └─ Normal trading range
  └─ Healthy trend if price above middle

Zone 3: Price below Lower Band
  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
  └─ Oversold (potential reversal up)
  └─ Or strong downtrend continuing

Band Squeeze Pattern (Pre-Breakout):
Time ──→

Normal:     ╱  ╲  ╱  ╲  ╱
          ╱    ╲╱    ╲╱

Squeeze:    ║││││││││║ ← Bands converge
            ║││││││││║    (low volatility)

Breakout:   ║││││╱╱╱╱║    (breakout direction)
            ║││││╱    or ║╲╲╲╲╲║
```

### 💡 Practical Usage

```python
# Calculate Bollinger Bands
def calculate_bb(prices, period=20, std_multiplier=2):
    sma = pd.Series(prices).rolling(period).mean()
    std = pd.Series(prices).rolling(period).std()
    
    upper = sma + (std_multiplier * std)
    lower = sma - (std_multiplier * std)
    
    return upper, sma, lower

df['bb_upper'], df['bb_middle'], df['bb_lower'] = \
    calculate_bb(df['close'].values)

# Example 1: Squeeze Detection (breakout setup)
df['band_width'] = df['bb_upper'] - df['bb_lower']
df['band_width_sma'] = df['band_width'].rolling(20).mean()
df['squeeze'] = df['band_width'] < df['band_width_sma'] * 0.5

# Example 2: Mean Reversion in Ranging Market
df['price_above_upper'] = df['close'] > df['bb_upper']
df['price_below_lower'] = df['close'] < df['bb_lower']
df['mean_reversion_buy'] = df['price_below_lower'] & (df['close'] > df['close'].shift(1))
df['mean_reversion_sell'] = df['price_above_upper'] & (df['close'] < df['close'].shift(1))

# Example 3: Trend Confirmation
df['trend_up'] = df['close'] > df['bb_middle']
df['trend_down'] = df['close'] < df['bb_middle']

# Example 4: %B Oscillator (Position within bands)
df['%B'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
# %B > 0.8 = overbought, %B < 0.2 = oversold
```

### ⚙️ Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| **Period** | 20 | 10-50 range; shorter = more signals, longer = smoother |
| **Std Dev** | 2 | 1-3 range; 2.5 for tighter control, 1.5 for wider |

### ✅ Trading Tips

1. **Squeeze → Breakout** → Monitor for band expansion + price break
2. **Don't short overbought alone** → Strong trends can extend for months
3. **Use with momentum** → BB + RSI together more reliable
4. **Band touches aren't reversal signals** → Need confirmation (divergence, volume, pattern)

---

## 6. OBV (On Balance Volume)

**Category:** Volume | **Type:** Accumulation | **Timeframe:** 1h-Daily | **Best Used:** Confirming trends, detecting divergence

### 🎯 Intuition

**"Volume precedes price"** — OBV tracks cumulative buying vs selling volume.

- Rising OBV = institutions accumulating (bullish)
- Falling OBV = institutions distributing (bearish)
- OBV increasing while price stalls = reversal coming (bullish divergence)

Think of it as **invisible buying/selling force** building up before the price move happens.

### 📐 Mathematical Definition

```
OBV(t) = OBV(t-1) + Volume(t)   if Close(t) > Close(t-1)
       = OBV(t-1) - Volume(t)   if Close(t) < Close(t-1)
       = OBV(t-1)               if Close(t) = Close(t-1)

Simple rule:
- Green candle → ADD volume to OBV
- Red candle   → SUBTRACT volume from OBV
- Doji candle  → HOLD OBV (unchanged)

Example:
Day   Close  Prev  Volume  Direction    OBV_Change  OBV_Total
1     100    -     1000    -            0           0
2     101    100   1500    Up    (+)    +1500       1500
3     102    101   2000    Up    (+)    +2000       3500
4     101    102   800     Down  (-)    -800        2700
5     103    101   1200    Up    (+)    +1200       3900
6     102    103   1800    Down  (-)    -1800       2100
```

### 📊 Chart Interpretation

```
Price + OBV Chart:

Price:  ╱╲╱╱╲╱
       ╱  ╲╱  ╲╱

OBV:   ╱╱╱     ╱╱ ← Rising OBV (bullish accumulation)
      ╱╱╱     ╱╱
     /        \  ← Flat OBV (indecision)
    /          \ ← Falling OBV (bearish distribution)

Key Patterns:
┌─────────────────────────────────────────────┐
│ PATTERN                    │ MEANING         │
├─────────────────────────────────────────────┤
│ OBV rising, price rising   │ Confirmed uptrend│
│ OBV falling, price falling │ Confirmed dntrend│
│ OBV rising, price flat     │ Hidden strength │
│ OBV falling, price rising  │ Weakness ahead  │
│ OBV higher low, price LL   │ Bullish div    │
│ OBV lower high, price HH   │ Bearish div    │
└─────────────────────────────────────────────┘

Divergence Trading (Advanced):
Price falls to new low, but OBV doesn't
  = Sellers becoming exhausted
  = Reversal likely

Price rises to new high, but OBV doesn't
  = Buyers becoming exhausted
  = Reversal likely
```

### 💡 Practical Usage

```python
# Calculate OBV
def calculate_obv(close, volume):
    obv = np.zeros(len(close))
    obv[0] = volume[0]
    
    for i in range(1, len(close)):
        if close[i] > close[i-1]:
            obv[i] = obv[i-1] + volume[i]
        elif close[i] < close[i-1]:
            obv[i] = obv[i-1] - volume[i]
        else:
            obv[i] = obv[i-1]
    
    return obv

df['obv'] = calculate_obv(df['close'].values, df['volume'].values)

# Example 1: Trend Confirmation
df['price_up'] = df['close'] > df['close'].shift(1)
df['obv_up'] = df['obv'] > df['obv'].shift(1)
df['confirmed_uptrend'] = df['price_up'] & df['obv_up']

# Example 2: Volume Divergence (bullish)
df['price_new_low'] = df['low'] < df['low'].rolling(20).min()
df['obv_new_high'] = df['obv'] > df['obv'].rolling(20).max()
df['bullish_obv_divergence'] = df['price_new_low'] & df['obv_new_high']

# Example 3: OBV Momentum (EMA of OBV)
df['obv_ema'] = df['obv'].ewm(span=14).mean()
df['obv_momentum'] = df['obv_ema'].diff()  # Rate of change
df['obv_accelerating'] = df['obv_momentum'] > df['obv_momentum'].shift(1)
```

### ⚙️ Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| **Smoothing** | None | Can apply EMA-14 to OBV for cleaner signals |

---

## 7. VWAP (Volume Weighted Average Price)

**Category:** Volume / Trend | **Type:** Institutional Reference | **Timeframe:** Intraday | **Best Used:** Entry validation, institutional tracking

### 🎯 Intuition

VWAP is the **"fair value"** price according to institutional traders. It weights prices by volume.

- Price above VWAP → bullish bias (institutions accumulating at lower prices)
- Price below VWAP → bearish bias (institutions selling at higher prices)
- Price bounces off VWAP → strong dynamic support/resistance

Think of it as **the weighted center of gravity** of all trades that day.

### 📐 Mathematical Definition

```
VWAP = Σ(Price × Volume) / Σ(Volume)

Detailed calculation:
1. For each bar: Typical_Price = (High + Low + Close) / 3
2. Calculate: Typical_Price × Volume
3. Running sum: Σ(TP × V) and Σ(V)
4. VWAP = Cumulative(TP × V) / Cumulative(V)

Example Intraday:
Time    High  Low   Close  Volume  TP    TP×V      Cum_TPV  Cum_V   VWAP
9:30    100   99    99.5   1000    99.5  99500     99500    1000    99.50
9:35    100.5 99.5  100    2000    99.8  199600    299100   3000    99.70
9:40    101   100   100.5  2500    100.5 251250    550350   5500    100.06
9:45    101.5 100.5 101    3000    101   303000    853350   8500    100.39

VWAP climbs from 99.50 → 100.39 as day progresses
```

### 📊 Chart Interpretation

```
Intraday Chart with VWAP:

Price: ╱╱╱╱╱╱╱
      ╱╱╱╱╱╱╱
VWAP: ────────────────╲ ← Rising early, falling late (institutions unloading)

Key Patterns:
┌──────────────────────────────────────────┐
│ PRICE POSITION           │ INTERPRETATION  │
├──────────────────────────────────────────┤
│ Above VWAP all day       │ Strong buyers   │
│ Below VWAP all day       │ Strong sellers  │
│ Bouncing off VWAP        │ Support/resist  │
│ Break above VWAP + vol   │ Bullish breakout│
│ Break below VWAP + vol   │ Bearish break   │
└──────────────────────────────────────────┘
```

### 💡 Practical Usage

```python
# Calculate VWAP
def calculate_vwap(high, low, close, volume):
    tp = (high + low + close) / 3
    vwap = (tp * volume).cumsum() / volume.cumsum()
    return vwap

df['vwap'] = calculate_vwap(df['high'], df['low'], df['close'], df['volume'])

# Example 1: Institutional Bias
df['above_vwap'] = df['close'] > df['vwap']
df['institutional_bullish'] = df['above_vwap'] & (df['close'] > df['open'])

# Example 2: VWAP Support/Resistance
df['price_near_vwap'] = abs(df['close'] - df['vwap']) / df['close'] < 0.005
df['bounce_off_vwap'] = df['price_near_vwap'] & (df['close'] > df['open'])

# Example 3: Mean Reversion
df['distance_to_vwap'] = (df['close'] - df['vwap']) / df['vwap']
df['far_above_vwap'] = df['distance_to_vwap'] > 0.01  # 1% above
df['far_below_vwap'] = df['distance_to_vwap'] < -0.01  # 1% below
```

---

## 8. Stochastic Oscillator

**Category:** Momentum | **Type:** Oscillator | **Timeframe:** 4h-Daily | **Best Used:** Ranging markets, divergences

### 🎯 Intuition

Stochastic measures **where the current price sits within the recent range**.

- Close near highs → %K high (70+) → potential sell
- Close near lows → %K low (30-) → potential buy
- %K and %D crossing → momentum shift

Think of it as answering: *"Is price near the top or bottom of its recent trading range?"*

### 📐 Mathematical Definition

```
Step 1: Find highest high and lowest low over period (usually 14)
L14 = Lowest low over 14 bars
H14 = Highest high over 14 bars

Step 2: Calculate %K (fast stochastic)
%K = 100 × (Close - L14) / (H14 - L14)

Step 3: Smooth %K into %D (slow stochastic)
%D = SMA(%K, 3)

Interpretation:
- %K = 0%   : Price at 14-bar low
- %K = 50%  : Price at midpoint
- %K = 100% : Price at 14-bar high

Example:
Period: 14 bars
H14 = 105 (highest high)
L14 = 95  (lowest low)
Current close = 101

%K = 100 × (101 - 95) / (105 - 95)
   = 100 × 6 / 10
   = 60

Current price is 60% of the way from 14-bar low to high
```

### 📊 Chart Interpretation

```
Stochastic Chart:
100 ┌──────────────────┐ (Overbought)
 80 │      ╱╲  ╱╲      │
    │     ╱  ╲╱  ╲     │
%K  │    ╱    ╲    ╲   │
 50 |───────────────────| (Neutral)
    │   ╱      ╲    ╲  │
 20 │  ╱        ╲    ╲ │
    │ ╱          ╲    ╲│
  0 └──────────────────┘ (Oversold)

%K Line (fast): Responds quickly
%D Line (slow): Signal line, smoother

Key Patterns:
┌─────────────────────────────────────┐
│ PATTERN                    │ SIGNAL  │
├─────────────────────────────────────┤
│ %K > 80, then turns down   │ Sell   │
│ %K < 20, then turns up     │ Buy    │
│ %K crosses %D upward       │ Buy    │
│ %K crosses %D downward     │ Sell   │
│ %K/D in overbought, no div │ Caution│
└─────────────────────────────────────┘
```

### 💡 Practical Usage

```python
# Calculate Stochastic
def calculate_stochastic(high, low, close, period=14, smooth=3):
    lowest_low = low.rolling(period).min()
    highest_high = high.rolling(period).max()
    
    %K = 100 * (close - lowest_low) / (highest_high - lowest_low)
    %D = %K.rolling(smooth).mean()
    
    return %K, %D

df['%K'], df['%D'] = calculate_stochastic(df['high'], df['low'], df['close'])

# Example: Crossover signals
df['k_above_d'] = df['%K'] > df['%D']
df['kd_bullish_cross'] = (df['%K'] > df['%D']) & (df['%K'].shift(1) <= df['%D'].shift(1))
df['kd_bearish_cross'] = (df['%K'] < df['%D']) & (df['%K'].shift(1) >= df['%D'].shift(1))
```

---

# 🔵 ADVANCED INDICATORS

Advanced indicators combine multiple concepts for refined market analysis.

---

## 1. Ichimoku Cloud

**Category:** Trend | **Type:** Comprehensive | **Timeframe:** 4h-Daily | **Best Used:** Multi-level support/resistance, trend confirmation

### 🎯 Intuition

Ichimoku is a **complete trading system in one indicator** — it shows:
- Current support/resistance (Tenkan, Kijun)
- Trend direction (Cloud position)
- Historical context (Cloud thickness)
- Future levels (Leading span projection)

Think of it as a **full market snapshot** in one visual.

### 📐 Mathematical Definition

```
5 components:

1. Tenkan-sen (Conversion Line): 9-bar high-low midpoint
   Tenkan = (9-High + 9-Low) / 2
   
2. Kijun-sen (Base Line): 26-bar high-low midpoint
   Kijun = (26-High + 26-Low) / 2
   
3. Senkou Span A (Leading Span A): Average of Tenkan + Kijun, projected 26 bars forward
   Senkou_A = (Tenkan + Kijun) / 2  [shifted 26 periods ahead]
   
4. Senkou Span B (Leading Span B): 52-bar midpoint, projected 26 bars forward
   Senkou_B = (52-High + 52-Low) / 2  [shifted 26 periods ahead]
   
5. Chikou Span (Lagging Span): Close price shifted 26 bars backward
   Chikou = Close [shifted -26 periods]

Cloud = Area between Senkou A and Senkou B
```

### 📊 Chart Interpretation

```
Complete Ichimoku Setup:

Price ────────────────────────────── (current)
      Tenkan ╱╲╱  ← Fast line, current support
      Kijun ──╲─╱ ← Slow line, key level
             ╱╲╱╲╱
      Cloud ░░░░░░░░░ ← Future support/resistance
             ░░░░░░░░░
      
Chikou ────────────── ← Lagging (past price in future position)

Interpretation:
┌──────────────────────────────────┐
│ ELEMENT        │ MEANING         │
├──────────────────────────────────┤
│ Price > Cloud  │ Strong uptrend  │
│ Price < Cloud  │ Strong downtrend│
│ Cloud thick    │ Strong support  │
│ Cloud thin     │ Weak support    │
│ Tenkan > Kijun │ Short bullish   │
│ Tenkan < Kijun │ Short bearish   │
│ Chikou > Price │ Bullish signal  │
└──────────────────────────────────┘
```

### 💡 Practical Usage

```python
def calculate_ichimoku(high, low, close):
    # Tenkan-sen
    tenkan = ((high.rolling(9).max() + low.rolling(9).min()) / 2)
    
    # Kijun-sen
    kijun = ((high.rolling(26).max() + low.rolling(26).min()) / 2)
    
    # Senkou Span A
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    
    # Senkou Span B
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    
    # Chikou Span
    chikou = close.shift(-26)
    
    return tenkan, kijun, senkou_a, senkou_b, chikou

df['tenkan'], df['kijun'], df['senkou_a'], df['senkou_b'], df['chikou'] = \
    calculate_ichimoku(df['high'], df['low'], df['close'])

# Trading signals
df['price_above_cloud'] = df['close'] > df[['senkou_a', 'senkou_b']].max(axis=1)
df['cloud_bullish'] = df['senkou_a'] > df['senkou_b']
df['tenkan_above_kijun'] = df['tenkan'] > df['kijun']

# Strong signal: Price > Cloud AND Tenkan > Kijun
df['strong_uptrend'] = df['price_above_cloud'] & df['tenkan_above_kijun']
```

---

## 2. Supertrend

**Category:** Trend | **Type:** Binary | **Timeframe:** Any | **Best Used:** Trend following, stop placement

### 🎯 Intuition

Supertrend is a **volatility-adjusted trend line** that flips between uptrend and downtrend.

- When in uptrend → line is below price (support)
- When in downtrend → line is above price (resistance)
- Line changes color → trend reversal confirmed

Think of it as an **automated stop-loss line** that moves with volatility.

### 📐 Mathematical Definition

```
Step 1: Calculate Basic Upper and Lower Bands
HL2 = (High + Low) / 2
Basic_Upper = HL2 + (Multiplier × ATR)
Basic_Lower = HL2 - (Multiplier × ATR)

Step 2: Calculate Final Bands (using previous values)
Final_Upper = Basic_Upper if Basic_Upper < Final_Upper[prev] or Close[prev] > Final_Upper[prev]
            else Final_Upper[prev]

Final_Lower = Basic_Lower if Basic_Lower > Final_Lower[prev] or Close[prev] < Final_Lower[prev]
            else Final_Lower[prev]

Step 3: Determine Supertrend
Supertrend = Final_Upper if Trend is DOWN and Close crosses below
           = Final_Lower if Trend is UP and Close crosses above
```

### 📊 Chart Interpretation

```
Price + Supertrend:

Uptrend:        Price ╱╱╱╱╱╱╱
               Supertrend ────── ← Below price (support)

Reversal:       Price ╱╱╱╱╲╲
               Supertrend ────╲╲ ← Crosses below = sell

Downtrend:      Price ╲╲╲╲╲╲
               Supertrend ────── ← Above price (resistance)
```

---

## 3. CCI (Commodity Channel Index)

**Category:** Momentum | **Type:** Deviation | **Timeframe:** Any | **Best Used:** Extremes, mean reversion

### 🎯 Intuition

CCI measures **how far price has deviated from its average**.

- CCI > 100 → price extremely high (potential sell)
- CCI < -100 → price extremely low (potential buy)
- CCI between -100 and 100 → normal range

### 📐 Mathematical Definition

```
Step 1: Typical Price
TP = (High + Low + Close) / 3

Step 2: Simple MA of TP
TP_SMA = SMA(TP, 20)

Step 3: Mean Absolute Deviation
MAD = Sum(|TP - TP_SMA|) / 20

Step 4: CCI
CCI = (TP - TP_SMA) / (0.015 × MAD)

0.015 is a constant for normalization
```

---

## 4. Donchian Channel

**Category:** Breakout | **Type:** Extremes | **Timeframe:** Any | **Best Used:** Breakout confirmation, range trading

### 🎯 Intuition

Donchian Channel marks the **highest high and lowest low over N periods**.

- Price breaks above upper band → upside breakout (buy signal)
- Price breaks below lower band → downside breakout (sell signal)
- Price bouncing between bands → range-bound

### 📐 Mathematical Definition

```
Upper = Highest_High(last 20 bars)
Lower = Lowest_Low(last 20 bars)
Middle = (Upper + Lower) / 2
```

---

## 5. Keltner Channel

**Category:** Volatility | **Type:** Dynamic Envelope | **Timeframe:** Any | **Best Used:** Volatility-adjusted trading, breakout confirmation

### 🎯 Intuition

Similar to Bollinger Bands but uses **ATR instead of standard deviation**.

- Smoother than Bollinger Bands
- Better for volatile assets
- ATR-based = accounts for gaps

### 📐 Mathematical Definition

```
Middle = EMA(Close, 20)
Upper = Middle + (ATR(10) × 2)
Lower = Middle - (ATR(10) × 2)

More responsive to gaps than Bollinger Bands
```

---

## 6. HMA (Hull Moving Average)

**Category:** Trend | **Type:** Low-lag MA | **Timeframe:** Any | **Best Used:** Fast trend changes, reduced lag

### 🎯 Intuition

HMA reduces **lag of moving averages** while keeping smoothness.

Combines:
- Fast WMA (responsive)
- Slow WMA (smooth)
- Weighted difference

Result: Faster turns than SMA/EMA, smoother than price.

### 📐 Mathematical Definition

```
HMA = WMA(2 × WMA(n/2) - WMA(n), sqrt(n))

WMA = Weighted Moving Average (closer bars weighted more)

Effective lag: sqrt(period) instead of period/2
Much faster! SMA-20 lags ≈10 bars, HMA-20 lags ≈4.5 bars
```

---

## 7. KAMA (Kaufman Adaptive Moving Average)

**Category:** Trend | **Type:** Adaptive MA | **Timeframe:** 4h-Daily | **Best Used:** Trending markets, noise filtering

### 🎯 Intuition

KAMA **adapts its smoothing based on market conditions**:

- Trending market → fast response (responds to real moves)
- Choppy market → slow response (filters noise)

Think of it as an **intelligent moving average** that knows when to follow price and when to ignore it.

### 📐 Mathematical Definition

```
Step 1: Calculate Efficiency Ratio
Change = |Close - Close(n periods ago)|
Volatility = Sum(|Close - Close(1 period ago)|)
ER = Change / Volatility

ER ranges 0-1:
- ER = 1 → trending perfectly (no chop)
- ER = 0 → sideways chop (no trend)

Step 2: Calculate Smoothing Constant
Fastest_SC = 2 / (fast_period + 1) = 2/3 ≈ 0.67
Slowest_SC = 2 / (slow_period + 1) = 2/31 ≈ 0.065

Smoothed_SC = ER × (Fastest - Slowest) + Slowest
SSC = Smoothed_SC²

Step 3: Calculate KAMA
KAMA = KAMA(prev) + SSC × (Price - KAMA(prev))

If ER = 1 (trending):  SSC ≈ 0.45 (fast)
If ER = 0 (choppy):    SSC ≈ 0.004 (slow)
```

---

# 🧠 CORE MATHEMATICAL CONCEPTS

All technical indicators reduce to these fundamental operations:

## 1. **Smoothing**
Reducing noise while preserving trend

```
Techniques:
- SMA: Simple average (equal weight)
- EMA: Exponential (recent weight more)
- WMA: Weighted (linear decay)
- HMA: Hull (fast + accurate)

Use Case:
├─ Identify trend direction
├─ Find support/resistance
└─ Reduce whipsaws
```

## 2. **Normalization**
Converting values to a bounded range (usually 0-100 or -100 to +100)

```
Techniques:
- RSI: Gains vs losses → 0-100
- Stochastic: Position in range → 0-100
- CCI: Deviation → unbounded but typically -100 to +100

Use Case:
├─ Identify overbought/oversold
├─ Compare different timeframes
└─ Set consistent thresholds
```

## 3. **Deviation**
Measuring distance from average

```
Techniques:
- Bollinger Bands: Standard deviation × k
- CCI: Mean absolute deviation
- Keltner: ATR distance

Use Case:
├─ Identify volatility extremes
├─ Find breakout levels
└─ Detect consolidation
```

## 4. **Accumulation**
Building cumulative value over time

```
Techniques:
- OBV: Cumulative volume
- VWAP: Cumulative weighted price
- Ichimoku: Integrated multiple components

Use Case:
├─ Confirm price moves
├─ Detect institutional activity
└─ Find dynamic support/resistance
```

## 5. **Volatility Scaling**
Adapting sensitivity to market conditions

```
Techniques:
- ATR multipliers: Wider stops in volatile markets
- Keltner Channel: ATR-based envelopes
- KAMA: Efficiency ratio adaptation

Use Case:
├─ Dynamic stop placement
├─ Position sizing
└─ Breakout detection
```

---

# 📊 INDICATOR COMBINATIONS

## Strategy: Trend + Momentum + Volume

```python
# Complete trading system combining indicators

def analyze_market(df):
    """Multi-indicator analysis"""
    
    # 1. TREND (Direction)
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['is_uptrend'] = df['ema_20'] > df['ema_50']
    
    # 2. MOMENTUM (Speed)
    df['rsi'] = calculate_rsi(df['close'].values)
    df['overbought'] = df['rsi'] > 70
    df['oversold'] = df['rsi'] < 30
    
    # 3. VOLUME (Confirmation)
    df['obv'] = calculate_obv(df['close'].values, df['volume'].values)
    df['obv_trending'] = df['obv'] > df['obv'].shift(20)
    
    # 4. VOLATILITY (Risk)
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    df['stop_loss'] = df['close'] - (df['atr'] * 2)
    
    # 5. STRUCTURE (Entry)
    df['support'] = df['close'].rolling(20).min()
    df['resistance'] = df['close'].rolling(20).max()
    
    # COMPOSITE SIGNAL
    df['buy_signal'] = (
        (df['is_uptrend']) &           # Trending up
        (df['rsi'] < 60) &             # Not overbought
        (df['obv_trending']) &         # Volume confirming
        (df['close'] > df['support'])  # Above support
    )
    
    return df
```

---

# ⚠️ COMMON MISTAKES

## ❌ Don't:
1. **Use only one indicator** — always combine (trend + momentum + volume)
2. **Trade against the trend** — "overbought" ≠ sell signal in uptrend
3. **Ignore volume** — price moves without volume are fake
4. **Use default settings** — optimize for your market and timeframe
5. **Expect 100% accuracy** — no indicator is perfect
6. **Trade without stops** — indicator signals fail sometimes
7. **Overfit parameters** — causes poor real-time performance

## ✅ Do:
1. **Combine multiple indicators** — confluence of signals = higher probability
2. **Trade with the trend** — indicators confirm trend, not create it
3. **Always check volume** — volume confirms conviction
4. **Backtest thoroughly** — validate on historical data first
5. **Use appropriate timeframes** — 5m indicators ≠ daily charts
6. **Risk manage** — position size based on ATR, not emotion
7. **Keep systems simple** — fewer parameters = better generalization

---

# 🚀 QUICK REFERENCE

## By Market Condition:

### Trending Up
- **Trend Confirm:** EMA-20 > EMA-50, Price above both
- **Entry:** RSI < 60 (not overbought), OBV rising
- **Stop:** ATR × 2 below entry
- **Target:** Resistance level or 3× risk

### Trending Down
- **Trend Confirm:** EMA-20 < EMA-50, Price below both
- **Entry:** RSI > 40 (not oversold), OBV falling
- **Stop:** ATR × 2 above entry
- **Target:** Support level or 3× risk

### Consolidation/Range
- **Entry:** RSI < 30 buy, RSI > 70 sell
- **Levels:** Upper = 20-bar high, Lower = 20-bar low
- **Target:** Opposite band or 1× risk
- **Exit:** Volume break + close outside band

### Low Volatility Squeeze
- **Setup:** Bollinger Band width < 50th percentile
- **Trigger:** Volume spike + candle break band
- **Direction:** Usually follows prior trend
- **Target:** Opposite band or breakout direction

---

# 📚 References & Further Learning

- **Technical Analysis from A to Z** - Pring
- **Market Profile** - Steidlmayer
- **Volume Profile** - Rogers
- **Ichimoku Mastery** - Buffaloe

---

**Last Updated:** 2026
**License:** MIT
**Contributions:** Welcome!