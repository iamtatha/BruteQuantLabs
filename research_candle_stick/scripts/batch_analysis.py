"""
Batch Candlestick Pattern Analysis with SQLite Storage

Analyzes multiple stocks and stores results in SQLite database.
Organized by stock with separate tables for patterns and summary stats.
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from pathlib import Path


import sys
from pathlib import Path
import logging

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from analysis_scripts.utils.candles import detect_candles_claude
from research_candle_stick.scripts.candle_stick_pattern_efficiency import analyze_candlestick_patterns
        


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


class StockPatternAnalyzer:
    """Analyze candlestick patterns for multiple stocks and store in SQLite."""
    
    def __init__(
        self, 
        db_path: str = "database/bql_pattern_analysis.db",
        create_tables: bool = True
    ):
        """
        Initialize the analyzer.
        
        Parameters:
        -----------
        db_path : str
            Path to SQLite database file
        create_tables : bool
            If True, create tables on init
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if create_tables:
            self.create_database_schema()
    

    def create_database_schema(self):
        """Create database tables for storing pattern analysis results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        
        # ========================
        # ANALYSIS METADATA TABLE
        # ========================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL UNIQUE,
                industry TEXT,
                min_conf_threshold REAL,
                min_price_change_pct REAL,
                use_valid_only INTEGER,
                analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        

        # ========================
        # PATTERN STATISTICS TABLE
        # ========================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_stats (
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
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stock_code, pattern_name, direction)
            )
        """)
        
        # ========================
        # HIGH-PERFORMANCE PATTERNS TABLE
        # ========================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS high_performance_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                gap_days INTEGER,
                accuracy REAL,
                win_rate REAL,
                avg_max_return REAL,
                expected_value REAL,
                total_occurrences INTEGER,
                
                -- Pattern qualifies if: accuracy > 60% AND win_rate > 55%
                quality_score REAL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ========================
        # PATTERN OUTCOMES TABLE (Raw Data)
        # ========================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                pattern_date TEXT NOT NULL,
                pattern_price REAL,
                confidence REAL,
                
                -- Price at different gaps
                price_7d REAL,
                price_14d REAL,
                price_30d REAL,
                
                -- Outcome at different gaps
                bullish_7d INTEGER,
                bullish_14d INTEGER,
                bullish_30d INTEGER,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        

        # ========================
        # INDUSTRY PATTERN SUMMARY TABLE (NEW)
        # ========================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_pattern_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                industry TEXT NOT NULL,
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
                
                num_stocks_with_pattern INTEGER,
                stock_consistency REAL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(industry, pattern_name, direction),
                FOREIGN KEY (industry) REFERENCES industry_summary(industry)
            )
        """)


        # ========================
        # INDUSTRY PATTERN SUMMARY TABLE (NEW)
        # ========================
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS industry_pattern_summary (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         industry TEXT NOT NULL,
        #         pattern_name TEXT NOT NULL,
        #         direction TEXT NOT NULL,
        #         num_stocks_with_pattern INTEGER,
        #         total_occurrences INTEGER,
                
        #         -- Aggregated 7-day metrics
        #         avg_accuracy_7d REAL,
        #         min_accuracy_7d REAL,
        #         max_accuracy_7d REAL,
        #         avg_win_rate_7d REAL,
        #         avg_max_return_7d REAL,
                
        #         -- Aggregated 14-day metrics
        #         avg_accuracy_14d REAL,
        #         min_accuracy_14d REAL,
        #         max_accuracy_14d REAL,
        #         avg_win_rate_14d REAL,
        #         avg_max_return_14d REAL,
                
        #         -- Aggregated 30-day metrics
        #         avg_accuracy_30d REAL,
        #         min_accuracy_30d REAL,
        #         max_accuracy_30d REAL,
        #         avg_win_rate_30d REAL,
        #         avg_max_return_30d REAL,
                
        #         -- Quality metrics
        #         consistency_score REAL,
        #         reliability_rank INTEGER,
                
        #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        #         UNIQUE(industry, pattern_name, direction)
        #     )
        # """)
        
        conn.commit()
        conn.close()
        print(f"✓ Database schema created at {self.db_path}")
    

    def analyze_and_store_batch(
        self,
        stock_dataframes: Dict[str, pd.DataFrame],
        stock_industries: Dict[str, str],
        detect_func,
        day_gaps: List[int] = [7, 14, 30],
        min_conf_threshold: float = 0.0,
        min_price_change_pct: float = 0.01,
        use_valid_only: bool = True,
        focus_patterns: List[str] = None,
        calculate_sharpe: bool = True,
        debug: bool = False
    ):
        """
        Analyze multiple stocks and store results in SQLite.
        
        Parameters:
        -----------
        stock_dataframes : Dict[str, pd.DataFrame]
            Dictionary of {stock_code: df}
        detect_func : callable
            Pattern detection function
        day_gaps : List[int]
            Time horizons to analyze
        min_conf_threshold : float
            Minimum confidence threshold
        min_price_change_pct : float
            Minimum price change percentage
        use_valid_only : bool
            Use only validated patterns
        focus_patterns : List[str], optional
            Specific patterns to analyze
        calculate_sharpe : bool
            Calculate Sharpe ratio
        debug : bool
            Print debug info
        """
        total_stocks = len(stock_dataframes)
        processed = 0
        
        print(f"\n{'='*70}")
        print(f"BATCH ANALYSIS: {total_stocks} stocks")
        print(f"{'='*70}\n")
        
        for stock_code, df in stock_dataframes.items():
            try:
                processed += 1
                print(f"[{processed}/{total_stocks}] Analyzing {stock_code}...", end=" ")
                
                # Analyze stock
                result = analyze_candlestick_patterns(
                    df=df,
                    detect_func=detect_func,
                    stock_name=stock_code,
                    day_gaps=day_gaps,
                    min_conf_threshold=min_conf_threshold,
                    min_price_change_pct=min_price_change_pct,
                    use_valid_only=use_valid_only,
                    focus_patterns=focus_patterns,
                    calculate_sharpe=calculate_sharpe,
                    debug=debug
                )
                
                # Store results
                self._store_stock_results(
                    result,
                    stock_code,
                    stock_industries.get(stock_code, "Unknown"),
                    min_conf_threshold,
                    min_price_change_pct,
                    use_valid_only
                )
                
                print(f"✓ ({result.n_patterns_detected} patterns)")
                
            except Exception as e:
                print(f"✗ ERROR: {str(e)}")
                if debug:
                    import traceback
                    traceback.print_exc()
        
        # ========================
        # After all stocks analyzed, compute industry summaries
        # ========================
        print(f"\n{'='*70}")
        print("Computing industry summaries...")
        print(f"{'='*70}")
        self._compute_industry_summaries()
    

    def _store_stock_results(
        self,
        result,
        stock_code: str,
        stock_industry: str,
        min_conf_threshold: float,
        min_price_change_pct: float,
        use_valid_only: bool
    ):
        """Store analysis results for a single stock in SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # ========================
            # 2. STORE PATTERN STATISTICS
            # ========================
            for key, stat in result.pattern_stats.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO pattern_stats
                    (stock_code, pattern_name, direction, total_occurrences,
                     accuracy_7d, win_rate_7d, avg_max_return_7d, expected_value_7d,
                     accuracy_14d, win_rate_14d, avg_max_return_14d, expected_value_14d,
                     accuracy_30d, win_rate_30d, avg_max_return_30d, expected_value_30d)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stock_code,
                    stat.pattern_name,
                    stat.direction,
                    stat.total_occurrences,
                    # 7-day
                    stat.accuracy_rate_7d,
                    stat.win_rate_7d,
                    stat.avg_max_return_7d,
                    stat.expected_value_7d,
                    # 14-day
                    stat.accuracy_rate_14d,
                    stat.win_rate_14d,
                    stat.avg_max_return_14d,
                    stat.expected_value_14d,
                    # 30-day
                    stat.accuracy_rate_30d,
                    stat.win_rate_30d,
                    stat.avg_max_return_30d,
                    stat.expected_value_30d,
                ))
            
            # ========================
            # 3. STORE HIGH-PERFORMANCE PATTERNS
            # ========================
            for key, stat in result.pattern_stats.items():
                for gap, accuracy_attr, win_rate_attr, return_attr, expval_attr in [
                    (7, 'accuracy_rate_7d', 'win_rate_7d', 'avg_max_return_7d', 'expected_value_7d'),
                    (14, 'accuracy_rate_14d', 'win_rate_14d', 'avg_max_return_14d', 'expected_value_14d'),
                    (30, 'accuracy_rate_30d', 'win_rate_30d', 'avg_max_return_30d', 'expected_value_30d'),
                ]:
                    accuracy = getattr(stat, accuracy_attr)
                    win_rate = getattr(stat, win_rate_attr)
                    avg_return = getattr(stat, return_attr)
                    expval = getattr(stat, expval_attr)
                    
                    # Store if high performance: accuracy > 60% AND win_rate > 55%
                    if accuracy > 0.60 and win_rate > 0.55:
                        quality_score = (accuracy * 0.6 + win_rate * 0.4) * avg_return
                        
                        cursor.execute("""
                            INSERT INTO high_performance_patterns
                            (stock_code, pattern_name, direction, gap_days,
                             accuracy, win_rate, avg_max_return, expected_value,
                             total_occurrences, quality_score)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            stock_code,
                            stat.pattern_name,
                            stat.direction,
                            gap,
                            accuracy,
                            win_rate,
                            avg_return,
                            expval,
                            stat.total_occurrences,
                            quality_score,
                        ))
            
            # ========================
            # 4. STORE PATTERN OUTCOMES (sample, not all)
            # ========================
            # Store only high-confidence outcomes (limit to 1000 per stock to save space)
            high_conf_outcomes = [o for o in result.outcomes if o.confidence >= min_conf_threshold][:1000]
            
            for outcome in high_conf_outcomes:
                cursor.execute("""
                    INSERT INTO pattern_outcomes
                    (stock_code, pattern_name, direction, pattern_date, pattern_price, confidence,
                     price_7d, price_14d, price_30d,
                     bullish_7d, bullish_14d, bullish_30d)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stock_code,
                    outcome.pattern_name,
                    outcome.direction,
                    outcome.pattern_date,
                    outcome.pattern_price,
                    outcome.confidence,
                    outcome.price_7d if not np.isnan(outcome.price_7d) else None,
                    outcome.price_14d if not np.isnan(outcome.price_14d) else None,
                    outcome.price_30d if not np.isnan(outcome.price_30d) else None,
                    int(outcome.bullish_7d) if not np.isnan(outcome.bullish_7d) else None,
                    int(outcome.bullish_14d) if not np.isnan(outcome.bullish_14d) else None,
                    int(outcome.bullish_30d) if not np.isnan(outcome.bullish_30d) else None,
                ))
            
            # ========================
            # 5. STORE ANALYSIS METADATA
            # ========================
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_metadata
                (stock_code, industry, min_conf_threshold, min_price_change_pct, use_valid_only)
                VALUES (?, ?, ?, ?, ?)
            """, (
                stock_code,
                stock_industry,
                min_conf_threshold,
                min_price_change_pct,
                int(use_valid_only),
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    
    def _compute_industry_summaries(self):
        """Compute aggregated statistics by industry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all unique industries
            cursor.execute("SELECT DISTINCT industry FROM analysis_metadata WHERE industry IS NOT NULL")
            industries = [row[0] for row in cursor.fetchall()]
            
            for industry in industries:
                # Get all stocks in this industry
                # cursor.execute("""
                #     SELECT stock_code, accuracy_7d, accuracy_14d, accuracy_30d,
                #            avg_max_return_7d, avg_max_return_14d, avg_max_return_30d,
                #            n_patterns
                #     FROM stock_summary
                #     WHERE industry = ?
                # """, (industry,))
                
                # stocks = cursor.fetchall()
                # if not stocks:
                #     continue
                
                # num_stocks = len(stocks)
                
                # # Find best pattern for this industry
                # cursor.execute("""
                #     SELECT ps.pattern_name, ps.direction, ps.accuracy_7d, 7 as gap
                #     FROM pattern_stats ps
                #     JOIN stock_summary ss ON ps.stock_code = ss.stock_code
                #     WHERE ss.industry = ? AND ps.accuracy_7d > 0.60
                #     ORDER BY ps.accuracy_7d DESC
                #     LIMIT 1
                # """, (industry,))
                

                
                # ========================
                # COMPUTE PER-PATTERN SUMMARY FOR THIS INDUSTRY
                # ========================
                
                # Get all patterns in this industry
                cursor.execute("""
                    SELECT DISTINCT ps.pattern_name, ps.direction
                    FROM pattern_stats ps
                    JOIN analysis_metadata ss ON ps.stock_code = ss.stock_code
                    WHERE ss.industry = ?
                    ORDER BY ps.pattern_name, ps.direction
                """, (industry,))
                
                patterns = cursor.fetchall()
                
                for pattern_name, direction in patterns:
                    # Get stats for this pattern in this industry
                    cursor.execute("""
                        SELECT 
                            COUNT(DISTINCT ps.stock_code) as num_stocks,
                            SUM(ps.total_occurrences) as total_occurrences,
                            AVG(ps.accuracy_7d) as avg_acc_7d,
                            MIN(ps.accuracy_7d) as min_acc_7d,
                            MAX(ps.accuracy_7d) as max_acc_7d,
                            AVG(ps.win_rate_7d) as avg_wr_7d,
                            AVG(ps.avg_max_return_7d) as avg_ret_7d,
                            AVG(ps.accuracy_14d) as avg_acc_14d,
                            MIN(ps.accuracy_14d) as min_acc_14d,
                            MAX(ps.accuracy_14d) as max_acc_14d,
                            AVG(ps.win_rate_14d) as avg_wr_14d,
                            AVG(ps.avg_max_return_14d) as avg_ret_14d,
                            AVG(ps.accuracy_30d) as avg_acc_30d,
                            MIN(ps.accuracy_30d) as min_acc_30d,
                            MAX(ps.accuracy_30d) as max_acc_30d,
                            AVG(ps.win_rate_30d) as avg_wr_30d,
                            AVG(ps.avg_max_return_30d) as avg_ret_30d
                        FROM pattern_stats ps
                        JOIN analysis_metadata ss ON ps.stock_code = ss.stock_code
                        WHERE ss.industry = ? AND ps.pattern_name = ? AND ps.direction = ?
                    """, (industry, pattern_name, direction))
                    
                    stats = cursor.fetchone()
                    if not stats or not stats[0]:  # Skip if no data
                        continue
                    
                    (num_stocks, total_occ, avg_acc_7d, min_acc_7d, max_acc_7d, avg_wr_7d, avg_ret_7d,
                     avg_acc_14d, min_acc_14d, max_acc_14d, avg_wr_14d, avg_ret_14d,
                     avg_acc_30d, min_acc_30d, max_acc_30d, avg_wr_30d, avg_ret_30d) = stats
                    
                    # Calculate consistency score (0-1): how consistent across stocks
                    # High when min/max are close, low when they vary
                    consistency_7d = 1 - (max_acc_7d - min_acc_7d) if (max_acc_7d and min_acc_7d) else 0
                    consistency_14d = 1 - (max_acc_14d - min_acc_14d) if (max_acc_14d and min_acc_14d) else 0
                    consistency_30d = 1 - (max_acc_30d - min_acc_30d) if (max_acc_30d and min_acc_30d) else 0
                    consistency_score = np.mean([c for c in [consistency_7d, consistency_14d, consistency_30d] if c])
                    
                    # Reliability rank: patterns ranked by accuracy in industry
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM (
                            SELECT ps.pattern_name, ps.direction, AVG(ps.accuracy_7d) as avg_acc
                            FROM pattern_stats ps
                            JOIN analysis_metadata ss ON ps.stock_code = ss.stock_code
                            WHERE ss.industry = ?
                            GROUP BY ps.pattern_name, ps.direction
                            HAVING avg_acc >= ?
                            ORDER BY avg_acc DESC
                        )
                    """, (industry, avg_acc_7d))
                    
                    reliability_rank = cursor.fetchone()[0]
                    
                    # Insert industry pattern summary
                    expected_value_7d = (avg_acc_7d * avg_wr_7d * avg_ret_7d) if (avg_acc_7d and avg_wr_7d and avg_ret_7d) else None
                    expected_value_14d = (avg_acc_14d * avg_wr_14d * avg_ret_14d) if (avg_acc_14d and avg_wr_14d and avg_ret_14d) else None
                    expected_value_30d = (avg_acc_30d * avg_wr_30d * avg_ret_30d) if (avg_acc_30d and avg_wr_30d and avg_ret_30d) else None
                    
                    stock_consistency = num_stocks / num_stocks  # All stocks have this pattern
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO industry_pattern_summary
                        (industry, pattern_name, direction, total_occurrences, num_stocks_with_pattern, stock_consistency,
                         accuracy_7d, win_rate_7d, avg_max_return_7d, expected_value_7d,
                         accuracy_14d, win_rate_14d, avg_max_return_14d, expected_value_14d,
                         accuracy_30d, win_rate_30d, avg_max_return_30d, expected_value_30d)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        industry, pattern_name, direction, int(total_occ) if total_occ else 0, num_stocks, stock_consistency,
                        avg_acc_7d, avg_wr_7d, avg_ret_7d, expected_value_7d,
                        avg_acc_14d, avg_wr_14d, avg_ret_14d, expected_value_14d,
                        avg_acc_30d, avg_wr_30d, avg_ret_30d, expected_value_30d
                    ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            print(f"Error computing industry summaries: {e}")
            raise e
        finally:
            conn.close()
    

    def get_industry_pattern_summary(self, industry: str) -> pd.DataFrame:
        """Get summary of all patterns in a specific industry."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT industry, pattern_name, direction, num_stocks_with_pattern, total_occurrences,
                   accuracy_7d, win_rate_7d, avg_max_return_7d, expected_value_7d,
                   accuracy_14d, win_rate_14d, avg_max_return_14d, expected_value_14d,
                   accuracy_30d, win_rate_30d, avg_max_return_30d, expected_value_30d,
                   stock_consistency
            FROM industry_pattern_summary
            WHERE industry = ?
            ORDER BY accuracy_7d DESC, accuracy_14d DESC, accuracy_30d DESC
        """
        df = pd.read_sql_query(query, conn, params=(industry,))
        
        conn.close()
        return df


    def get_stocks_by_industry(self, industry: str) -> pd.DataFrame:
        """Get all stocks in a specific industry with their metrics."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT stock_code, industry, n_patterns,
                   accuracy_7d, accuracy_14d, accuracy_30d,
                   avg_max_return_7d, avg_max_return_14d, avg_max_return_30d
            FROM analysis_metadata
            WHERE industry = ?
            ORDER BY accuracy_7d DESC
        """
        df = pd.read_sql_query(query, conn, params=(industry,))
        
        conn.close()
        return df


    def get_high_performance_patterns(
        self,
        stock_code: str = None,
        gap_days: int = 7,
        min_quality_score: float = 0.0
    ) -> pd.DataFrame:
        """Get high-performance patterns."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT stock_code, pattern_name, direction, gap_days,
                   accuracy, win_rate, avg_max_return, expected_value,
                   total_occurrences, quality_score
            FROM high_performance_patterns
            WHERE gap_days = ? AND quality_score >= ?
        """
        params = [gap_days, min_quality_score]
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        
        query += " ORDER BY quality_score DESC"
        df = pd.read_sql_query(query, conn, params=params)
        
        conn.close()
        return df
    

    def get_pattern_stats(
        self,
        stock_code: str = None,
        pattern_name: str = None,
        min_occurrences: int = 10
    ) -> pd.DataFrame:
        """Get pattern statistics."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT stock_code, pattern_name, direction, total_occurrences,
                   accuracy_7d, win_rate_7d, avg_max_return_7d,
                   accuracy_14d, win_rate_14d, avg_max_return_14d,
                   accuracy_30d, win_rate_30d, avg_max_return_30d
            FROM pattern_stats
            WHERE total_occurrences >= ?
        """
        params = [min_occurrences]
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        
        if pattern_name:
            query += " AND pattern_name = ?"
            params.append(pattern_name)
        
        query += " ORDER BY total_occurrences DESC"
        df = pd.read_sql_query(query, conn, params=params)
        
        conn.close()
        return df
    

    def export_to_csv(self, table_name: str, output_path: str):
        """Export a table to CSV."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        # Create output directory if it doesn't exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False)
        print(f"✓ Exported {table_name} to {output_path}")








def load_stock_codes_industries(v):
    DIR = "database/static_data"
    if v != 450:
        file_path = f"{DIR}/nifty_{v}.csv"
        try:
            df = pd.read_csv(file_path)
            stock_codes = df["Symbol"].tolist()
            stock_industries = {
                row["Symbol"]: row["Industry"] for _, row in df.iterrows()
            }
            print("Loaded stock codes and industries for Nifty", v)
            return stock_codes, stock_industries
        except FileNotFoundError:
            return None, None

    else:
        try:
            nifty_500_path = f"{DIR}/nifty_500.csv"
            nifty_500_list = pd.read_csv(nifty_500_path)["Symbol"].tolist()

            nifty_50_path = f"{DIR}/nifty_50.csv"
            nifty_50_list = pd.read_csv(nifty_50_path)["Symbol"].tolist()
            stock_codes = [ele for ele in nifty_500_list if ele not in nifty_50_list]
            stock_industries = {
                row["Symbol"]: row["Industry"] for _, row in df.iterrows()
            }
            print("Loaded stock codes and industries for Nifty 500 (excluding Nifty 50)")
            return stock_codes, stock_industries
        except FileNotFoundError:
            return None, None



PRICES_DIR = "database/historical_data_yf"

def load_data(stock_code="TCS"):
    file_path = f"{PRICES_DIR}/{stock_code}.NS_yf.json"
    try:
        df = pd.read_json(file_path).T
    except FileNotFoundError:
        return None
    
    dates = pd.to_datetime(df.index.tolist()).tolist()
    
    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock_code}.NS", '').lower() for c in cols]
    df.columns = cols
    print("Loaded data for", stock_code)
    return df





# print(load_stock_codes(450))
# print(load_stock_codes(500))
# print(load_stock_codes_industries(50))




def run(stock_dataframes, stock_industries, stock_codes, db_path="database/bql_candle_stick_analysis.db"):
    # Create analyzer
    analyzer = StockPatternAnalyzer(db_path="database/bql_candle_stick_analysis.db")

    # Analyze and store
    analyzer.analyze_and_store_batch(
        stock_dataframes=stock_dataframes,
        stock_industries=stock_industries,
        detect_func=detect_candles_claude,
        day_gaps=[7, 14, 30],
        min_conf_threshold=0.5,
        use_valid_only=True,
        debug=True
    )

    # Query results
    print("\n" + "="*70)
    print("QUERY EXAMPLES")
    print("="*70)



    # Get high-performance patterns
    top_patterns = analyzer.get_high_performance_patterns(gap_days=7, min_quality_score=0.5)
    print("\nTop High-Performance Patterns (7-day):")
    print(top_patterns.head(10))





# stock_codes = ["TCS", "INFY", "WIPRO"]
# # stock_codes = ["TCS"]

# stock_dataframes = {
#     code: load_data(stock_code=code)[0]
#     for code in stock_codes
# }
# stock_industries = {
#     "TCS": "IT",
#     "INFY": "IT",
#     "WIPRO": "IT"
# }




stock_codes, stock_industries = load_stock_codes_industries(500)

stock_dataframes = {}

for stock_code in stock_codes:
    stock_dataframes[stock_code] = load_data(stock_code=stock_code)



run(stock_dataframes, stock_industries, stock_codes)
