"""
REFACTORED OLD STRATEGIES
=========================

This file contains the two strategies from your original code,
refactored to use the new framework.

Original file had:
1. BollingerBandStrategy (~150 lines)
2. StochasticTradingStrategy (~150 lines)

Refactored versions: ~20 lines each
"""

"""
Source: https://github.com/petkosamoletko/Trading_Strategies_Backtest_Stochastic_Oscillator_and_Bollinger_Bands
petkosamoletko
"""




import sys
from pathlib import Path

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import backtrader as bt
from research_indicators.strategies_util.base_strategy import BaseStrategy
from research_indicators.strategies_util.backtest_engine import BacktestEngine
import math
import datetime
import pandas as pd


# ============================================================================
# STRATEGY 1: Bollinger Band Strategy (Refactored)
# ============================================================================

class BollingerBandStrategyRefactored(BaseStrategy):
    """
    Bollinger Band Strategy - Refactored Version
    
    Original: ~150 lines with all boilerplate
    Refactored: ~30 lines, inheriting from BaseStrategy
    
    Buy Signal:
        - Price > 200 SMA (trend filter)
        - Price < Lower Bollinger Band (oversold)
        - Uses limit order at 3% discount
    
    Sell Signal:
        - Held for 10 days OR
        - RSI > 50
    """
    
    params = (
        ('sma_period', 200),
        ('bb_period', 20),
        ('bb_devfactor', 2.5),
        ('rsi_period', 2),
        ('limit_discount', 0.97),
        ('holding_days', 10),
        ('rsi_exit', 50),
    )
    
    def __init__(self):
        super().__init__()
        
        # Indicators
        self.moving_avg = bt.ind.SMA(period=self.p.sma_period)
        self.boll_bands = bt.ind.BollingerBands(
            period=self.p.bb_period, 
            devfactor=self.p.bb_devfactor
        )
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period, safediv=True)
    
    def buy_signal(self) -> bool:
        """Buy when price is above SMA and below lower Bollinger Band"""
        return (self.dataclose[0] > self.moving_avg[0] and 
                self.dataclose[0] < self.boll_bands.lines.bot[0])
    
    def sell_signal(self) -> bool:
        """Sell after 10 days or when RSI > 50"""
        days_held = len(self) - self.bar_executed
        return days_held >= self.p.holding_days or self.rsi[0] > self.p.rsi_exit
    
    def execute_buy(self):
        """Execute buy with limit order at 3% discount"""
        target_price = self.dataclose[0] * self.p.limit_discount
        qty = self.calculate_position_size(target_price, percentage=1.0)  # ← FIXED: Use 100%
        
        if qty > 0:
            self.log(f'BUY CREATE - Target: {target_price:.2f}, Qty: {qty}')
            self.order = self.buy(
                exectype=bt.Order.Limit,
                price=target_price,
                size=qty
            )
            self.qty_sell_track = 0


# ============================================================================
# STRATEGY 2: Stochastic Strategy (Refactored)
# ============================================================================

class StochasticTradingStrategyRefactored(BaseStrategy):
    """
    Stochastic Oscillator Strategy - Refactored Version
    
    Original: ~150 lines with all boilerplate
    Refactored: ~30 lines, inheriting from BaseStrategy
    
    Buy Signal:
        - Price > 200 SMA (trend filter)
        - Stochastic %K <= 5 (oversold)
        - Uses limit order at 3% discount with 5-day validity
    
    Sell Signal:
        - Held for 10 days OR
        - Price closes above buy target price
    """
    
    params = (
        ('sma_period', 200),
        ('stoch_period', 10),
        ('stoch_dfast', 1),
        ('stoch_dslow', 1),
        ('stoch_oversold', 5),
        ('limit_discount', 0.97),
        ('holding_days', 10),
        ('limit_valid_days', 5),
    )
    
    def __init__(self):
        super().__init__()
        
        # Indicators
        self.moving_avg = bt.ind.SMA(period=self.p.sma_period)
        self.stochastic = bt.ind.Stochastic(
            self.datas[0],
            period=self.p.stoch_period,
            period_dfast=self.p.stoch_dfast,
            period_dslow=self.p.stoch_dslow
        )
        self.stochastic_k = self.stochastic.percK
        
        # Track target price for this strategy
        self.target_price = None
    
    def buy_signal(self) -> bool:
        """Buy when price > SMA and Stochastic K <= 5"""
        return (self.dataclose[0] > self.moving_avg[0] and 
                self.stochastic_k[0] <= self.p.stoch_oversold)
    
    def sell_signal(self) -> bool:
        """Sell after 10 days or when price > target"""
        days_held = len(self) - self.bar_executed
        
        price_target_hit = (self.target_price is not None and 
                           self.dataclose[0] > self.target_price)
        
        return days_held >= self.p.holding_days or price_target_hit
    
    def execute_buy(self):
        """Execute buy with limit order at 3% discount, valid for 5 days"""
        self.target_price = self.dataclose[0] * self.p.limit_discount
        qty = self.calculate_position_size(self.target_price, percentage=1.0)
        
        if qty > 0:
            self.log(f'BUY CREATE - Target: {self.target_price:.2f}, Qty: {qty}')
            
            valid_duration = datetime.timedelta(days=self.p.limit_valid_days)
            
            self.order = self.buy(
                exectype=bt.Order.Limit,
                price=self.target_price,
                valid=valid_duration,
                size=qty
            )
            self.qty_sell_track = 0


# ============================================================================
# CONVENIENCE FUNCTIONS TO RUN THE REFACTORED STRATEGIES
# ============================================================================

def run_bollinger_band_strategy(stock_code: str, 
                                data_loader_func,
                                years: int = 5,
                                initial_cash: float = 12000.0,
                                plot: bool = True,
                                **params):
    """
    Run the refactored Bollinger Band strategy
    
    Args:
        stock_code: Stock ticker
        data_loader_func: Function to load price data
        years: Years of historical data
        initial_cash: Starting cash
        plot: Whether to plot results
        **params: Override default strategy parameters
        
    Returns:
        Results dictionary
        
    Example:
        >>> from utils.dataloader import load_prices
        >>> results = run_bollinger_band_strategy(
        ...     'TCS', 
        ...     load_prices, 
        ...     years=5,
        ...     sma_period=200,
        ...     holding_days=15
        ... )
    """
    
    
    # Load data
    df, dates, cols = data_loader_func(stock_code, years=years)
    feed = bt.feeds.PandasData(dataname=df)
    
    # Run backtest
    engine = BacktestEngine(initial_cash=initial_cash)
    results = engine.run_strategy(
        strategy_class=BollingerBandStrategyRefactored,
        data_feed=feed,
        strategy_params=params,
        plot=plot,
        verbose=True
    )
    
    return results


def run_stochastic_strategy(stock_code: str,
                           data_loader_func,
                           years: int = 5,
                           initial_cash: float = 12000.0,
                           plot: bool = True,
                           **params):
    """
    Run the refactored Stochastic strategy
    
    Args:
        stock_code: Stock ticker
        data_loader_func: Function to load price data
        years: Years of historical data
        initial_cash: Starting cash
        plot: Whether to plot results
        **params: Override default strategy parameters
        
    Returns:
        Results dictionary
        
    Example:
        >>> from utils.dataloader import load_prices
        >>> results = run_stochastic_strategy(
        ...     'TCS',
        ...     load_prices,
        ...     years=5,
        ...     stoch_oversold=10,
        ...     holding_days=15
        ... )
    """
    
    # Load data
    df, dates, cols = data_loader_func(stock_code, years=years)
    feed = bt.feeds.PandasData(dataname=df)
    
    # Run backtest
    engine = BacktestEngine(initial_cash=initial_cash)
    results = engine.run_strategy(
        strategy_class=StochasticTradingStrategyRefactored,
        data_feed=feed,
        strategy_params=params,
        plot=plot,
        verbose=True
    )
    
    return results


def compare_both_old_strategies(stock_code: str,
                                data_loader_func,
                                years: int = 5,
                                initial_cash: float = 12000.0):
    """
    Compare both refactored strategies side by side
    
    Example:
        >>> from utils.dataloader import load_prices
        >>> compare_both_old_strategies('TCS', load_prices, years=5)
    """
    
    # Load data
    df, dates, cols = data_loader_func(stock_code, years=years)
    feed = bt.feeds.PandasData(dataname=df)
    
    engine = BacktestEngine(initial_cash=initial_cash)
    
    results = []
    
    # Run Bollinger Band Strategy
    print("\n" + "="*60)
    print("Testing: Bollinger Band Strategy (Refactored)")
    print("="*60)
    result1 = engine.run_strategy(
        strategy_class=BollingerBandStrategyRefactored,
        data_feed=feed,
        plot=False,
        verbose=True
    )
    result1['strategy'] = 'Bollinger Band'
    results.append(result1)
    
    # Run Stochastic Strategy
    print("\n" + "="*60)
    print("Testing: Stochastic Strategy (Refactored)")
    print("="*60)
    result2 = engine.run_strategy(
        strategy_class=StochasticTradingStrategyRefactored,
        data_feed=feed,
        plot=False,
        verbose=True
    )
    result2['strategy'] = 'Stochastic'
    results.append(result2)
    
    # Create comparison DataFrame
    df_results = pd.DataFrame(results)
    
    print("\n" + "="*60)
    print("STRATEGY COMPARISON")
    print("="*60)
    
    comparison = df_results[[
        'strategy',
        'total_return_pct',
        'annualized_return_pct',
        'sharpe_ratio',
        'max_drawdown_pct',
        'win_rate',
        'total_trades',
        'profit_factor'
    ]]
    
    comparison.columns = [
        'Strategy',
        'Return %',
        'Ann. Return %',
        'Sharpe',
        'Max DD %',
        'Win Rate %',
        'Trades',
        'Profit Factor'
    ]
    
    print(comparison.to_string(index=False))
    print("="*60 + "\n")
    
    return df_results


# ============================================================================
# MAIN EXECUTION - Run this file directly to test
# ============================================================================

if __name__ == "__main__":
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Import your data loader
    from utils.dataloader import load_prices
    
    # Example 1: Run Bollinger Band Strategy
    print("\n" + "#"*60)
    print("# EXAMPLE 1: Bollinger Band Strategy")
    print("#"*60)
    
    results_bb = run_bollinger_band_strategy(
        stock_code='TCS',
        data_loader_func=load_prices,
        years=5,
        initial_cash=12000,
        plot=False  # Set to True to see chart
    )





    
    
    # # Example 2: Run Stochastic Strategy
    # print("\n" + "#"*60)
    # print("# EXAMPLE 2: Stochastic Strategy")
    # print("#"*60)
    
    # results_stoch = run_stochastic_strategy(
    #     stock_code='TCS',
    #     data_loader_func=load_prices,
    #     years=5,
    #     initial_cash=12000,
    #     plot=False  # Set to True to see chart
    # )






    
    # # Example 3: Compare Both Strategies
    # print("\n" + "#"*60)
    # print("# EXAMPLE 3: Compare Both Strategies")
    # print("#"*60)
    
    # comparison_df = compare_both_old_strategies(
    #     stock_code='TCS',
    #     data_loader_func=load_prices,
    #     years=5,
    #     initial_cash=12000
    # )
    
    # # Example 4: Test with different parameters
    # print("\n" + "#"*60)
    # print("# EXAMPLE 4: Test with Custom Parameters")
    # print("#"*60)
    
    # results_custom = run_bollinger_band_strategy(
    #     stock_code='TCS',
    #     data_loader_func=load_prices,
    #     years=5,
    #     initial_cash=12000,
    #     plot=False,
    #     holding_days=15,  # Custom parameter
    #     rsi_exit=60       # Custom parameter
    # )