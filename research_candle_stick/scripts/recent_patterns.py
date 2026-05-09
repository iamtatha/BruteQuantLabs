"""
Recent High-Performance Pattern Analysis
Analyzes candlestick patterns from the last N days and computes performance metrics.
Writes results back to database.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class RecentPatternMetrics:
    """Metrics for recent pattern performance."""
    pattern_name: str
    direction: str
    stock_code: str
    total_occurrences: int
    accuracy_7d: float
    win_rate_7d: float
    avg_max_return_7d: float
    expected_value_7d: float
    
    accuracy_14d: float
    win_rate_14d: float
    avg_max_return_14d: float
    expected_value_14d: float
    
    accuracy_30d: float
    win_rate_30d: float
    avg_max_return_30d: float
    expected_value_30d: float
    
    quality_score_7d: float
    quality_score_14d: float
    quality_score_30d: float
    
    first_pattern_date: str
    last_pattern_date: str
    analysis_date: str


def analyze_recent_patterns(
    db_path: str = "database/bql_candle_stick_analysis.db",
    n_days: int = 90
) -> pd.DataFrame:
    """
    Analyze high-performance candlestick patterns from the last N days.
    
    Parameters:
    -----------
    db_path : str
        Path to the SQLite database
    n_days : int
        Number of recent days to analyze (default: 90)
    
    Returns:
    --------
    pd.DataFrame with recent pattern metrics
    
    Process:
    1. Fetch all pattern outcomes from last N days
    2. Group by pattern + direction + stock
    3. Calculate 7d, 14d, 30d performance metrics
    4. Filter for high-performing patterns (accuracy > 60%, win_rate > 55%)
    5. Write results to 'recent_pattern_analysis' table in database
    """
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Delete table if it already exists
        cursor.execute("DROP TABLE IF EXISTS recent_pattern_analysis")
        
        
        # ========================
        # CREATE RESULTS TABLE IF NOT EXISTS
        # ========================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recent_pattern_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                total_occurrences INTEGER,
                
                -- 7-day metrics
                accuracy_7d REAL,
                win_rate_7d REAL,
                avg_max_return_7d REAL,
                expected_value_7d REAL,
                
                -- 14-day metrics
                accuracy_14d REAL,
                win_rate_14d REAL,
                avg_max_return_14d REAL,
                expected_value_14d REAL,
                
                -- 30-day metrics
                accuracy_30d REAL,
                win_rate_30d REAL,
                avg_max_return_30d REAL,
                expected_value_30d REAL,
                
                -- Quality scores
                quality_score_7d REAL,
                quality_score_14d REAL,
                quality_score_30d REAL,
                
                -- Date range
                first_pattern_date TEXT,
                last_pattern_date TEXT,
                days_analyzed INTEGER,
                
                -- Metadata
                analysis_date TEXT NOT NULL,
                is_high_performance INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(stock_code, pattern_name, direction, analysis_date)
            )
        """)
        conn.commit()
        
        # ========================
        # FETCH PATTERN OUTCOMES FROM LAST N DAYS
        # ========================
        cutoff_date = datetime.now() - timedelta(days=n_days)
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
        
        query = """
            SELECT 
                stock_code,  pattern_name, direction,
                pattern_date, pattern_price, confidence,
                price_7d, price_14d, price_30d,
                bullish_7d, bullish_14d, bullish_30d
            FROM pattern_outcomes
            WHERE pattern_date >= ?
            ORDER BY stock_code, pattern_name, direction, pattern_date
        """
        
        outcomes_df = pd.read_sql_query(query, conn, params=(cutoff_date_str,))
        
        if len(outcomes_df) == 0:
            print(f"No pattern outcomes found for the last {n_days} days")
            conn.close()
            return pd.DataFrame()
        
        print(f"✓ Fetched {len(outcomes_df)} pattern outcomes from last {n_days} days")
        
        # ========================
        # COMPUTE METRICS
        # ========================
        results = []
        
        # Group by stock + pattern + direction
        grouped = outcomes_df.groupby(['stock_code', 'pattern_name', 'direction'])

        # print(grouped.size().head())
        
        for (stock_code, pattern_name, direction), group in grouped:
            total_occ = len(group)
            
            if total_occ < 2:  # Need at least 2 occurrences for meaningful analysis
                # print(f"Skipping {stock_code}, {pattern_name}, {direction} - not enough occurrences")
                continue
            
            first_date = group['pattern_date'].min()
            last_date = group['pattern_date'].max()
            
            # ========================
            # 7-DAY METRICS
            # ========================
            valid_7d = group.dropna(subset=['price_7d'])
            # print(group)
            # print(valid_7d)

            if len(valid_7d) > 0:
                returns_7d = ((valid_7d['price_7d'] - valid_7d['pattern_price']) / 
                              valid_7d['pattern_price'] * 100)
                max_returns_7d = returns_7d.values
                
                # Accuracy (directional correctness)
                if direction == 'bullish':
                    correct_7d = sum(max_returns_7d > 0.5)
                else:  # bearish
                    correct_7d = sum(max_returns_7d < -0.5)
                
                accuracy_7d = correct_7d / len(max_returns_7d) if len(max_returns_7d) > 0 else 0.0
                
                # Win rate (profitable)
                win_count_7d = sum(max_returns_7d > 0) if direction == 'bullish' else sum(max_returns_7d < 0)
                win_rate_7d = win_count_7d / len(max_returns_7d) if len(max_returns_7d) > 0 else 0.0
                
                # Average max return
                avg_max_return_7d = np.mean(np.abs(max_returns_7d)) if len(max_returns_7d) > 0 else 0.0
                
                # Expected value
                expected_value_7d = accuracy_7d * win_rate_7d * avg_max_return_7d
                
                # Quality score
                quality_score_7d = (accuracy_7d * 0.6 + win_rate_7d * 0.4) * avg_max_return_7d
            else:
                accuracy_7d = win_rate_7d = avg_max_return_7d = expected_value_7d = quality_score_7d = None

            # print(f"7-Day Metrics for {stock_code}, {pattern_name}, {direction}:")
            # print(f"  Accuracy: {accuracy_7d}")
            # print(f"  Win Rate: {win_rate_7d}")
            # print(f"  Avg Max Return: {avg_max_return_7d}")
            # print(f"  Expected Value: {expected_value_7d}")
            # print(f"  Quality Score: {quality_score_7d}")

            # ========================
            # 14-DAY METRICS
            # ========================
            valid_14d = group.dropna(subset=['price_14d'])
            if len(valid_14d) > 0:
                returns_14d = ((valid_14d['price_14d'] - valid_14d['pattern_price']) / 
                               valid_14d['pattern_price'] * 100)
                max_returns_14d = returns_14d.values
                
                if direction == 'bullish':
                    correct_14d = sum(max_returns_14d > 0.5)
                else:
                    correct_14d = sum(max_returns_14d < -0.5)
                
                accuracy_14d = correct_14d / len(max_returns_14d) if len(max_returns_14d) > 0 else 0.0
                
                win_count_14d = sum(max_returns_14d > 0) if direction == 'bullish' else sum(max_returns_14d < 0)
                win_rate_14d = win_count_14d / len(max_returns_14d) if len(max_returns_14d) > 0 else 0.0
                
                avg_max_return_14d = np.mean(np.abs(max_returns_14d)) if len(max_returns_14d) > 0 else 0.0
                
                expected_value_14d = accuracy_14d * win_rate_14d * avg_max_return_14d
                
                quality_score_14d = (accuracy_14d * 0.6 + win_rate_14d * 0.4) * avg_max_return_14d
            else:
                accuracy_14d = win_rate_14d = avg_max_return_14d = expected_value_14d = quality_score_14d = None
            
            # ========================
            # 30-DAY METRICS
            # ========================
            valid_30d = group.dropna(subset=['price_30d'])
            if len(valid_30d) > 0:
                returns_30d = ((valid_30d['price_30d'] - valid_30d['pattern_price']) / 
                               valid_30d['pattern_price'] * 100)
                max_returns_30d = returns_30d.values
                
                if direction == 'bullish':
                    correct_30d = sum(max_returns_30d > 0.5)
                else:
                    correct_30d = sum(max_returns_30d < -0.5)
                
                accuracy_30d = correct_30d / len(max_returns_30d) if len(max_returns_30d) > 0 else 0.0
                
                win_count_30d = sum(max_returns_30d > 0) if direction == 'bullish' else sum(max_returns_30d < 0)
                win_rate_30d = win_count_30d / len(max_returns_30d) if len(max_returns_30d) > 0 else 0.0
                
                avg_max_return_30d = np.mean(np.abs(max_returns_30d)) if len(max_returns_30d) > 0 else 0.0
                
                expected_value_30d = accuracy_30d * win_rate_30d * avg_max_return_30d
                
                quality_score_30d = (accuracy_30d * 0.6 + win_rate_30d * 0.4) * avg_max_return_30d
            else:
                accuracy_30d = win_rate_30d = avg_max_return_30d = expected_value_30d = quality_score_30d = None
            
            # ========================
            # CHECK IF HIGH PERFORMANCE
            # ========================
            is_high_performance = 0
            if accuracy_7d and accuracy_7d > HIGH_PERF_ACC_THRESHOLD and win_rate_7d and win_rate_7d > HIGH_PERF_WIN_RATE_THRESHOLD:
                is_high_performance = 1
            
            # ========================
            # STORE RESULT
            # ========================
            results.append({
                'stock_code': stock_code,
                'pattern_name': pattern_name,
                'direction': direction,
                'total_occurrences': total_occ,
                'accuracy_7d': accuracy_7d,
                'win_rate_7d': win_rate_7d,
                'avg_max_return_7d': avg_max_return_7d,
                'expected_value_7d': expected_value_7d,
                'accuracy_14d': accuracy_14d,
                'win_rate_14d': win_rate_14d,
                'avg_max_return_14d': avg_max_return_14d,
                'expected_value_14d': expected_value_14d,
                'accuracy_30d': accuracy_30d,
                'win_rate_30d': win_rate_30d,
                'avg_max_return_30d': avg_max_return_30d,
                'expected_value_30d': expected_value_30d,
                'quality_score_7d': quality_score_7d,
                'quality_score_14d': quality_score_14d,
                'quality_score_30d': quality_score_30d,
                'first_pattern_date': first_date,
                'last_pattern_date': last_date,
                'is_high_performance': is_high_performance,
            })
        
        if not results:
            print(f"No patterns with >= 2 occurrences found")
            conn.close()
            return pd.DataFrame()
        
        results_df = pd.DataFrame(results)
        # print(results_df.head())
        print(f"✓ Computed metrics for {len(results_df)} unique patterns")
        
        # ========================
        # WRITE RESULTS TO DATABASE
        # ========================
        analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for _, row in results_df.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO recent_pattern_analysis
                (stock_code, pattern_name, direction, total_occurrences,
                 accuracy_7d, win_rate_7d, avg_max_return_7d, expected_value_7d,
                 accuracy_14d, win_rate_14d, avg_max_return_14d, expected_value_14d,
                 accuracy_30d, win_rate_30d, avg_max_return_30d, expected_value_30d,
                 quality_score_7d, quality_score_14d, quality_score_30d,
                 first_pattern_date, last_pattern_date, days_analyzed, analysis_date, is_high_performance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['stock_code'], row['pattern_name'], row['direction'],
                row['total_occurrences'],
                row['accuracy_7d'], row['win_rate_7d'], row['avg_max_return_7d'], row['expected_value_7d'],
                row['accuracy_14d'], row['win_rate_14d'], row['avg_max_return_14d'], row['expected_value_14d'],
                row['accuracy_30d'], row['win_rate_30d'], row['avg_max_return_30d'], row['expected_value_30d'],
                row['quality_score_7d'], row['quality_score_14d'], row['quality_score_30d'],
                row['first_pattern_date'], row['last_pattern_date'], n_days, analysis_date, row['is_high_performance']
            ))
        
        conn.commit()
        print(f"✓ Wrote {len(results_df)} results to 'recent_pattern_analysis' table")
        
        # ========================
        # DISPLAY SUMMARY
        # ========================
        high_perf = results_df[results_df['is_high_performance'] == 1]
        print(f"\n{'='*70}")
        print(f"RECENT PATTERN ANALYSIS SUMMARY ({n_days} days)")
        print(f"{'='*70}")
        print(f"\nTotal patterns analyzed: {len(results_df)}")
        print(f"High-performance patterns: {len(high_perf)}")
        
        if len(high_perf) > 0:
            print(f"\n{'HIGH-PERFORMANCE PATTERNS (7-day)':<50}")
            print(f"{'-'*70}")
            print(high_perf[['stock_code', 'pattern_name', 'direction', 
                            'accuracy_7d', 'win_rate_7d', 'quality_score_7d']].to_string(index=False))
        
        conn.close()
        return results_df
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return pd.DataFrame()


def get_recent_patterns_from_db(
    db_path: str = "database/bql_candle_stick_analysis.db",
    high_performance_only: bool = False,
    gap_days: int = 7,
    min_quality_score: float = 0.0
) -> pd.DataFrame:
    """Query recent pattern analysis results from database."""
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM recent_pattern_analysis WHERE 1=1"
    params = []
    
    if high_performance_only:
        query += " AND is_high_performance = 1"
    
    if gap_days == 7:
        query += f" AND quality_score_7d >= ?"
        params.append(min_quality_score)
        query += " ORDER BY quality_score_7d DESC"
    elif gap_days == 14:
        query += f" AND quality_score_14d >= ?"
        params.append(min_quality_score)
        query += " ORDER BY quality_score_14d DESC"
    else:  # 30
        query += f" AND quality_score_30d >= ?"
        params.append(min_quality_score)
        query += " ORDER BY quality_score_30d DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# ========================
# USAGE EXAMPLES
# ========================


HIGH_PERF_ACC_THRESHOLD = 0
HIGH_PERF_WIN_RATE_THRESHOLD = 0

if __name__ == "__main__":
    # Analyze recent patterns (last 90 days)
    print("Analyzing recent candlestick patterns...\n")
    results = analyze_recent_patterns(
        db_path="database/bql_candle_stick_analysis.db",
        n_days=90
    )
    
    # Query results
    print("\n" + "="*70)
    print("QUERYING RESULTS")
    print("="*70)
    
    # All patterns
    all_patterns = get_recent_patterns_from_db()
    print(f"\nAll patterns analyzed: {len(all_patterns)}")
    
    # High-performance only
    high_perf = get_recent_patterns_from_db(high_performance_only=True, gap_days=7)
    print(f"High-performance patterns (7-day): {len(high_perf)}")
    if len(high_perf) > 0:
        print(high_perf[['stock_code',  'pattern_name', 'direction', 
                         'accuracy_7d', 'quality_score_7d']].head(10))
    
    # Top patterns by quality score
    top_patterns = get_recent_patterns_from_db(high_performance_only=True, gap_days=30, min_quality_score=2.0)
    print(f"\nTop patterns (30-day, quality_score > 2.0): {len(top_patterns)}")
    if len(top_patterns) > 0:
        print(top_patterns[['stock_code',  'pattern_name', 'direction', 
                           'accuracy_30d', 'quality_score_30d']].head(10))