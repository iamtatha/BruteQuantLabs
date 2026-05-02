# plot_valid_signals() - Updated with Confidence Scores

## Changes Made

### 1. **Annotations Tuple Structure**
**Before:**
```python
annotations.append((i, row["low"], "Hammer", "green"))
```

**After:**
```python
annotations.append((i, row["low"], "Hammer", "green", conf))
```
- Now includes confidence score as 5th element
- Confidence pulled from `{pattern}_valid_conf` columns

### 2. **Confidence Score Retrieval**
Added for each pattern:
```python
if row.get("hammer_valid", False):
    bullish_markers[i] = row["low"] * 0.995
    conf = row.get("hammer_valid_conf", 0.0)  # ← NEW
    annotations.append((i, row["low"], "Hammer", "green", conf))
```

Maps:
- `hammer_valid` → `hammer_valid_conf`
- `bullish_engulfing_valid` → `bullish_engulfing_valid_conf`
- `morning_star_valid` → `morning_star_valid_conf`
- `piercing_line` → `piercing_line_conf`
- `hanging_man_valid` → `hanging_man_valid_conf`
- `shooting_star_valid` → `shooting_star_valid_conf`
- `bearish_engulfing_valid` → `bearish_engulfing_valid_conf`
- `evening_star_valid` → `evening_star_valid_conf`
- `dark_cloud_cover` → `dark_cloud_cover_conf`

### 3. **Text Annotation with Confidence Badge**
**Before:**
```python
for x, y, text, color in annotations:
    ax.text(x, y_text, text, color=color, fontsize=8, ha="center", va="center")
```

**After:**
```python
for x, y, text, color, conf in annotations:
    label = f"{text}\n({conf:.2f})"  # Format: "Hammer\n(0.85)"
    
    ax.text(
        x, y_text, label,
        color=color,
        fontsize=8,
        ha="center",
        va="center",
        weight='bold',
        bbox=dict(
            boxstyle='round,pad=0.3',
            facecolor='white',
            edgecolor=color,
            alpha=0.8,
            linewidth=1
        )
    )
```

**Visual improvements:**
- Confidence displayed below pattern name: `Hammer\n(0.85)`
- Rounded box with colored border (matches pattern color)
- White background for readability
- Semi-transparent (alpha=0.8) to blend with chart
- Bold font for emphasis

### 4. **Marker Colors Explicit**
Added explicit color assignment to scatter plots:
```python
apds.append(
    mpf.make_addplot(
        bullish_markers,
        type='scatter',
        marker='^',
        markersize=80,
        color='green'  # ← NEW
    )
)
```

---

## Output Format

Each annotated pattern now displays as:

```
    Hammer
   (0.85)
    ↓ (marker)
```

Where:
- **Hammer** = pattern name
- **0.85** = confidence score (0.0 = no confidence, 1.0 = perfect)
- Label styled with rounded box, green or red border matching signal direction

---

## Confidence Score Interpretation

| Range | Interpretation |
|-------|----------------|
| 0.90 - 1.00 | Excellent signal, textbook pattern |
| 0.75 - 0.89 | Strong signal, high conviction |
| 0.60 - 0.74 | Good signal, moderate confidence |
| 0.40 - 0.59 | Weak signal, use with caution |
| 0.0 - 0.39 | Poor signal, low confidence |

**Trading Tip:** Filter to patterns with `conf >= 0.70` for higher win-rate signals.

---

## Usage Example

```python
# Detect patterns with custom thresholds
df_signals = detect_candles_claude(
    df,
    DOJI_THRESHOLD=0.10,
    HAMMER_LOWER_WICK_RATIO=2.5
)

# Plot with confidence scores
fig = plot_valid_signals(df_signals)
fig.show()
```

---

## What Changed in the Function

| Aspect | Before | After |
|--------|--------|-------|
| Annotation tuple | 4 elements | 5 elements (+ conf) |
| Confidence display | Not shown | Shown as (0.XX) in label |
| Text styling | Plain text | Rounded box with colored border |
| Font weight | Normal | Bold |
| Background | None | White box (alpha=0.8) |

---

## Backwards Compatibility

The function signature is **unchanged**:
```python
plot_valid_signals(df)  # Still same input
```

The function is a **drop-in replacement** — no breaking changes.

---

## Example Output Descriptions

### Bullish Signals (Green ▲)
- `Hammer\n(0.92)` = Hammer with 92% confidence
- `BullEng\n(0.78)` = Bullish Engulfing with 78% confidence
- `Morning★\n(0.85)` = Morning Star with 85% confidence
- `Piercing\n(0.65)` = Piercing Line with 65% confidence

### Bearish Signals (Red ▼)
- `HangMan\n(0.88)` = Hanging Man with 88% confidence
- `Shoot★\n(0.72)` = Shooting Star with 72% confidence
- `BearEng\n(0.81)` = Bearish Engulfing with 81% confidence
- `Evening★\n(0.77)` = Evening Star with 77% confidence
- `DarkCloud\n(0.69)` = Dark Cloud Cover with 69% confidence