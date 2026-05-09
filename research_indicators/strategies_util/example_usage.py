"""
Example Usage of the Backtesting Framework

This file demonstrates various ways to use the backtesting framework:
1. Running a single strategy
2. Comparing multiple strategies
3. Creating custom strategies
4. Running strategies on multiple stocks
"""

import sys
from pathlib import Path

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import logging
import backtrader as bt
from utils.dataloader import load_prices

from backtest_engine import (
    BacktestEngine, 
    run_backtest, 
    compare_strategies
)
from strategy_configs import (
    list_available_strategies,
    get_strategy_config
)
from strategy_factory import (
    create_strategy_from_config,
    create_custom_strategy
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/strategies.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Run a Single Strategy
# ============================================================================
def example_single_strategy():
    """Run a single predefined strategy"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Running a Single Strategy")
    print("="*80)
    
    results = run_backtest(
        stock_code='TCS',
        strategy_name='bollinger',  # Can be: bollinger, stochastic, rsi, ma_crossover, etc.
        data_loader_func=load_prices,
        years=10,
        initial_cash=100000,
        plot=True
    )
    
    print(f"\nFinal Return: {results['total_return_pct']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")


# ============================================================================
# EXAMPLE 2: Compare Multiple Strategies
# ============================================================================
def example_compare_strategies():
    """Compare multiple strategies on the same stock"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Comparing Multiple Strategies")
    print("="*80)
    
    # List all available strategies
    available = list_available_strategies()
    print(f"Available strategies: {available}")
    
    # Compare selected strategies
    strategies_to_test = ['bollinger', 'stochastic', 'rsi', 'ma_crossover']
    
    results_df = compare_strategies(
        stock_code='TCS',
        strategy_names=strategies_to_test,
        data_loader_func=load_prices,
        years=5,
        initial_cash=100000,
        plot_best=True,
        save_results=True
    )
    
    print("\nTop 3 Strategies:")
    print(results_df[['strategy_name', 'total_return_pct', 'sharpe_ratio', 'win_rate']].head(3))


# ============================================================================
# EXAMPLE 3: Create and Run a Custom Strategy
# ============================================================================
def example_custom_strategy():
    """Create a custom strategy from scratch"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Creating a Custom Strategy")
    print("="*80)
    
    # Define a custom strategy: Buy when RSI < 25, Sell when RSI > 75
    CustomStrategy = create_custom_strategy(
        name="AggressiveRSI",
        indicators={
            'rsi': (bt.ind.RSI, {'period': 14, 'safediv': True}),
            'sma': (bt.ind.SMA, {'period': 50})
        },
        buy_conditions=[
            lambda s: s.rsi[0] < 25,  # Very oversold
            lambda s: s.dataclose[0] > s.sma[0]  # Above 50 SMA
        ],
        sell_conditions=[
            lambda s: s.rsi[0] > 75  # Very overbought
        ],
        position_size_pct=0.90
    )
    
    # Load data
    df, dates, cols = load_prices('TCS', years=5)
    feed = bt.feeds.PandasData(dataname=df)
    
    # Run backtest
    engine = BacktestEngine(initial_cash=100000)
    results = engine.run_strategy(
        strategy_class=CustomStrategy,
        data_feed=feed,
        plot=True,
        verbose=True
    )
    
    print(f"\nCustom Strategy Results:")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Win Rate: {results['win_rate']:.2f}%")


# ============================================================================
# EXAMPLE 4: Test Strategy Across Multiple Stocks
# ============================================================================
def example_multi_stock_analysis():
    """Test the same strategy across multiple stocks"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Testing Strategy Across Multiple Stocks")
    print("="*80)
    
    stocks = ['TCS', 'INFY', 'WIPRO', 'HCLTECH']
    strategy_name = 'bollinger'
    
    results_summary = []
    
    for stock in stocks:
        print(f"\n{'-'*60}")
        print(f"Testing {stock}")
        print(f"{'-'*60}")
        
        try:
            results = run_backtest(
                stock_code=stock,
                strategy_name=strategy_name,
                data_loader_func=load_prices,
                years=3,
                initial_cash=100000,
                plot=False
            )
            
            results_summary.append({
                'stock': stock,
                'return_pct': results['total_return_pct'],
                'sharpe': results['sharpe_ratio'],
                'win_rate': results['win_rate'],
                'total_trades': results['total_trades']
            })
            
        except Exception as e:
            print(f"Error testing {stock}: {e}")
            continue
    
    # Display summary
    import pandas as pd
    df_summary = pd.DataFrame(results_summary)
    df_summary = df_summary.sort_values('return_pct', ascending=False)
    
    print("\n" + "="*80)
    print("MULTI-STOCK SUMMARY")
    print("="*80)
    print(df_summary.to_string(index=False))


# ============================================================================
# EXAMPLE 5: Advanced - Custom Strategy with Multiple Indicators
# ============================================================================
def example_advanced_custom_strategy():
    """Create a more complex custom strategy"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Advanced Custom Strategy")
    print("="*80)
    
    # Create a strategy that combines multiple indicators
    AdvancedStrategy = create_custom_strategy(
        name="MultiIndicator",
        indicators={
            'sma_fast': (bt.ind.SMA, {'period': 20}),
            'sma_slow': (bt.ind.SMA, {'period': 50}),
            'rsi': (bt.ind.RSI, {'period': 14, 'safediv': True}),
            'macd': (bt.ind.MACD, {'period_me1': 12, 'period_me2': 26, 'period_signal': 9}),
            'bbands': (bt.ind.BollingerBands, {'period': 20, 'devfactor': 2})
        },
        buy_conditions=[
            # Trend: Fast SMA above Slow SMA
            lambda s: s.sma_fast[0] > s.sma_slow[0],
            # Momentum: RSI oversold
            lambda s: s.rsi[0] < 40,
            # MACD bullish
            lambda s: s.macd.macd[0] > s.macd.signal[0],
            # Price near lower Bollinger Band
            lambda s: s.dataclose[0] < s.bbands.lines.mid[0]
        ],
        sell_conditions=[
            # Exit when RSI overbought
            lambda s: s.rsi[0] > 70,
            # Or MACD bearish
            lambda s: (s.macd.macd[0] < s.macd.signal[0] and 
                      s.macd.macd[-1] >= s.macd.signal[-1]),
            # Or 5% profit target
            lambda s: (s.buy_price and 
                      ((s.dataclose[0] - s.buy_price) / s.buy_price) >= 0.05)
        ],
        position_size_pct=0.95
    )
    
    # Load data
    df, dates, cols = load_prices('TCS', years=5)
    feed = bt.feeds.PandasData(dataname=df)
    
    # Run backtest
    engine = BacktestEngine(initial_cash=100000)
    results = engine.run_strategy(
        strategy_class=AdvancedStrategy,
        data_feed=feed,
        plot=True,
        verbose=True
    )


# ============================================================================
# EXAMPLE 6: Batch Testing - All Strategies on One Stock
# ============================================================================
def example_batch_test_all_strategies():
    """Test all available strategies on one stock"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Testing All Available Strategies")
    print("="*80)
    
    all_strategies = list_available_strategies()
    
    results_df = compare_strategies(
        stock_code='TCS',
        strategy_names=all_strategies,
        data_loader_func=load_prices,
        years=5,
        initial_cash=100000,
        plot_best=True,
        save_results=True
    )
    
    # Export to CSV for further analysis
    results_df.to_csv('all_strategies_comparison.csv', index=False)
    print("\nResults exported to 'all_strategies_comparison.csv'")


# ============================================================================
# Main Execution
# ============================================================================
if __name__ == "__main__":
    
    # Run examples (comment/uncomment as needed)
    
    # Example 1: Single strategy
    # example_single_strategy()
    
    # Example 2: Compare strategies
    # example_compare_strategies()
    
    # Example 3: Custom strategy
    # example_custom_strategy()
    
    # Example 4: Multi-stock analysis
    example_multi_stock_analysis()
    
    # Example 5: Advanced custom strategy
    # example_advanced_custom_strategy()
    
    # Example 6: Batch test all strategies
    # example_batch_test_all_strategies()
