# 📊 Technical Indicators Library (Detailed)

This document defines **primary and advanced indicators** with:

* Category & Type
* Intuition
* Mathematical formulation
* Derivation insight
* Graph interpretation

---

# 🟢 PRIMARY INDICATORS

---

## 1. Moving Averages (SMA / EMA)

* **Category:** Trend
* **Type:** Primary

### 📌 Intuition

Smooth noisy price into a trend line.

### 📐 Formula

* SMA:
  [
  SMA_t = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}
  ]

* EMA:
  [
  EMA_t = \alpha P_t + (1-\alpha) EMA_{t-1}, \quad \alpha = \frac{2}{n+1}
  ]

### 🔍 Derivation Insight

* SMA = simple averaging → equal weight
* EMA = exponential decay → recent prices weighted more

### 📊 Graph Meaning

* SMA → smoother, laggy line
* EMA → faster response to price changes
* Crossovers show **trend transitions**

---

## 2. RSI (Relative Strength Index)

* **Category:** Momentum
* **Type:** Primary

### 📌 Intuition

Measures **relative strength of buying vs selling**

### 📐 Formula

[
RS = \frac{\text{Avg Gain}}{\text{Avg Loss}}
]
[
RSI = 100 - \frac{100}{1 + RS}
]

### 🔍 Derivation Insight

* Converts price changes into **bounded oscillator (0–100)**
* Normalization avoids scale issues

### 📊 Graph Meaning

* Oscillates between 0–100
* Above 70 → strong buying (overextended)
* Below 30 → strong selling

---

## 3. MACD

* **Category:** Trend + Momentum
* **Type:** Primary

### 📌 Intuition

Measures **difference between short-term and long-term momentum**

### 📐 Formula

[
MACD = EMA_{12} - EMA_{26}
]
[
Signal = EMA_9(MACD)
]
[
Histogram = MACD - Signal
]

### 🔍 Derivation Insight

* EMA difference ≈ **velocity of price trend**
* Signal line smooths noise

### 📊 Graph Meaning

* MACD crossing signal → trend shift
* Histogram expansion → momentum increasing

---

## 4. ATR (Average True Range)

* **Category:** Volatility
* **Type:** Primary

### 📌 Intuition

Measures **how much price moves**, not direction

### 📐 Formula

[
TR = \max(H-L, |H-C_{prev}|, |L-C_{prev}|)
]
[
ATR = SMA(TR)
]

### 🔍 Derivation Insight

* Captures **gaps + intraday movement**
* Avoids underestimating volatility

### 📊 Graph Meaning

* High ATR → volatile market
* Low ATR → consolidation

---

## 5. Bollinger Bands

* **Category:** Volatility
* **Type:** Primary

### 📌 Intuition

Price tends to stay within statistical bounds

### 📐 Formula

[
Middle = SMA
]
[
Upper = SMA + k\sigma
]
[
Lower = SMA - k\sigma
]

### 🔍 Derivation Insight

* Based on **standard deviation (variance)**
* Expands/contracts with volatility

### 📊 Graph Meaning

* Band squeeze → low volatility → breakout likely
* Price touching bands → potential reversal

---

## 6. OBV (On Balance Volume)

* **Category:** Volume
* **Type:** Primary

### 📌 Intuition

Volume precedes price

### 📐 Formula

[
OBV_t =
\begin{cases}
OBV_{t-1} + V_t & \text{if } P_t > P_{t-1} \
OBV_{t-1} - V_t & \text{if } P_t < P_{t-1}
\end{cases}
]

### 🔍 Derivation Insight

* Converts volume into **cumulative flow signal**

### 📊 Graph Meaning

* Rising OBV → accumulation
* Divergence → early reversal signal

---

## 7. VWAP

* **Category:** Volume / Trend
* **Type:** Primary

### 📌 Intuition

Institutional “fair price”

### 📐 Formula

[
VWAP = \frac{\sum (Price \times Volume)}{\sum Volume}
]

### 🔍 Derivation Insight

* Weighted average → large trades matter more

### 📊 Graph Meaning

* Price above VWAP → bullish bias
* Mean-reversion anchor

---

## 8. Stochastic Oscillator

* **Category:** Momentum
* **Type:** Primary

### 📐 Formula

[
%K = \frac{C - L_n}{H_n - L_n}
]

### 🔍 Insight

Measures **position in range**, not direction

### 📊 Graph Meaning

* Fast oscillator → reacts quickly
* Good in ranging markets

---

# 🔵 ADVANCED INDICATORS

---

## 1. Ichimoku Cloud

* **Category:** Trend
* **Type:** Advanced

### 📐 Components

[
Tenkan = \frac{High_9 + Low_9}{2}
]
[
Kijun = \frac{High_{26} + Low_{26}}{2}
]

### 🔍 Derivation Insight

* Uses **midpoints of ranges**, not averages
* Encodes trend + support/resistance

### 📊 Graph Meaning

* Cloud = dynamic support/resistance
* Thickness = strength

---

## 2. Supertrend

* **Category:** Trend
* **Type:** Advanced

### 📐 Formula

[
Upper = \frac{H+L}{2} + k \cdot ATR
]

### 🔍 Insight

* ATR defines volatility-adjusted trend

### 📊 Graph Meaning

* Line flips → trend reversal

---

## 3. CCI (Commodity Channel Index)

* **Category:** Momentum
* **Type:** Advanced

### 📐 Formula

[
CCI = \frac{TP - SMA}{0.015 \cdot MAD}
]

### 🔍 Insight

* Measures **deviation from mean**

### 📊 Graph Meaning

* Large deviation → extreme condition

---

## 4. Donchian Channel

* **Category:** Breakout
* **Type:** Advanced

### 📐 Formula

[
Upper = \max(H_n), \quad Lower = \min(L_n)
]

### 📊 Graph Meaning

* Break above → breakout
* Used in trend-following systems

---

## 5. Keltner Channel

* **Category:** Volatility
* **Type:** Advanced

### 📐 Formula

[
Upper = EMA + ATR
]

### 🔍 Insight

* Similar to Bollinger but smoother

---

## 6. HMA (Hull Moving Average)

* **Category:** Trend
* **Type:** Advanced

### 📐 Idea

[
HMA = WMA(2 \cdot WMA(n/2) - WMA(n))
]

### 🔍 Insight

* Reduces lag + smoothness tradeoff

---

## 7. KAMA (Adaptive MA)

* **Category:** Trend
* **Type:** Advanced

### 📐 Idea

Adapts smoothing factor using:
[
Efficiency = \frac{Price Change}{Volatility}
]

### 🔍 Insight

* Faster in trends, slower in noise

---

# 🧠 CORE MATHEMATICAL THEMES

All indicators reduce to:

* **Smoothing (EMA, SMA)**
* **Normalization (RSI, Stochastic)**
* **Deviation (Bollinger, CCI)**
* **Accumulation (OBV, VWAP)**
* **Volatility scaling (ATR)**

---

# 📊 HOW TO READ INDICATORS ON A GRAPH

* Trend indicators → follow price
* Oscillators → move in bounded range
* Volume indicators → confirm moves
* Volatility → expand/contract

---

# ⚠️ FINAL INSIGHT

Indicators are transformations:

[
f(\text{price, volume}) \rightarrow \text{features}
]

Not predictions.

---

# 🚀 BEST PRACTICE

Use combination:

```text
Trend + Momentum + Volume + Volatility + Structure
```

Instead of stacking similar indicators.

---
