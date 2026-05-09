"""
Backtesting Engine
Main engine for running and comparing multiple strategies
"""

import sys
from pathlib import Path
import backtrader as bt
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
import matplotlib.pyplot as plt
from datetime import datetime
import json

from research_indicators.strategies_util.base_strategy import BaseStrategy
from research_indicators.strategies_util.strategy_configs import get_strategy_config, list_available_strategies
from research_indicators.strategies_util.strategy_factory import create_strategy_from_config
from research_indicators.strategies_util.enhanced_visualizations import visualize_backtest_results


class FixedCommission(bt.CommInfoBase):
    """
    Fixed commission model
    Can be customized for different brokers/markets
    """
    params = (
        ('commission', 10),
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED)
    )
    
    def _getcommission(self, size, price, pseudoexec):
        return self.p.commission
    

class PercentageCommission(bt.CommInfoBase):
    """
    Percentage-based commission model (e.g., 1% of trade value)
    Default: 0.01 (1%)
    """
    params = (
        ('commission', 0.01),  # 1% = 0.01
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_PERC)  # ← Changed to COMM_PERC
    )
    
    def _getcommission(self, size, price, pseudoexec):
        return abs(size) * price * self.p.commission


class BacktestEngine:
    """
    Main backtesting engine
    Handles running strategies and collecting results
    """
    
    def __init__(self, 
                 initial_cash: Optional[float] = None,  # ← Changed to Optional
                 commission: float = 0.01,
                 commission_type: str = 'percentage',
                 normalized_mode: bool = False):  # ← New parameter
        """
        Initialize backtesting engine
        
        Args:
            initial_cash: Starting portfolio value (if None, uses 100000 for normalized mode)
            commission: Commission amount
            commission_type: Type of commission ('fixed', 'percentage')
            normalized_mode: If True, focuses on % returns, sets cash to 100000 automatically
        """
        if normalized_mode or initial_cash is None:
            self.initial_cash = 100000.0  # Standard base for % calculations
            self.normalized_mode = True
        else:
            self.initial_cash = initial_cash
            self.normalized_mode = normalized_mode
            
        self.commission = commission
        self.commission_type = commission_type
        self.results = []
    
    def run_strategy(self,
                    strategy_class,
                    data_feed: bt.feeds.PandasData,
                    strategy_params: Optional[Dict] = None,
                    plot: bool = False,
                    enhanced_plot: bool = False,
                    verbose: bool = True) -> Dict[str, Any]:
        """
        Run a single strategy backtest
        
        Args:
            strategy_class: Strategy class to run
            data_feed: Backtrader data feed
            strategy_params: Optional parameters for the strategy
            plot: Whether to plot results
            enhanced_plot: Whether to use enhanced visualizations
            verbose: Whether to print detailed logs
        
        Returns:
            Dictionary containing results and metrics
        """
        # Create cerebro instance
        cerebro = bt.Cerebro()
        
        # Add strategy
        if strategy_params:
            cerebro.addstrategy(strategy_class, **strategy_params)
        else:
            cerebro.addstrategy(strategy_class)
        
        # Add data
        cerebro.adddata(data_feed)
        
        # Set initial cash
        cerebro.broker.setcash(self.initial_cash)
        
        # Add commission
        if self.commission_type == 'percentage':
            comminfo = PercentageCommission(commission=self.commission)
            cerebro.broker.addcommissioninfo(comminfo)
        elif self.commission_type == 'fixed':
            # Keep the old fixed commission for backward compatibility
            class FixedCommission(bt.CommInfoBase):
                params = (
                    ('commission', self.commission),
                    ('stocklike', True),
                    ('commtype', bt.CommInfoBase.COMM_FIXED)
                )
                def _getcommission(self, size, price, pseudoexec):
                    return self.p.commission
            
            comminfo = FixedCommission()
            cerebro.broker.addcommissioninfo(comminfo)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Run backtest
        start_value = cerebro.broker.getvalue()
        if verbose:
            print(f"\nStarting Portfolio Value: ₹{start_value:,.2f}")
        
        results = cerebro.run()
        strategy_result = results[0]
        
        end_value = cerebro.broker.getvalue()
        if verbose:
            print(f"Final Portfolio Value: ₹{end_value:,.2f}")
        
        # Collect results
        result_dict = self._collect_results(
            strategy_result, 
            start_value, 
            end_value,
            verbose
        )
        
        # Plot if requested
        if plot:
            cerebro.plot(style='candlestick')

        # Enhanced plot if requested
        if enhanced_plot:
            try:
                # Get original dataframe from feed
                df = data_feed.p.dataname
                strategy_name = strategy_class.__name__.replace('Strategy', '')
                
                visualize_backtest_results(
                    df=df,
                    results=result_dict,
                    strategy_name=strategy_name,
                    show_all=True,
                    show_equity=True,
                    show_trades=True,
                    save_pdf=True        # Save as PDF
                )
            except ImportError:
                print("Enhanced visualizations not available. Install required packages or use plot=True for basic plotting.")
        
        return result_dict
    
    def run_multiple_strategies(self,
                               strategy_names: List[str],
                               data_feed: bt.feeds.PandasData,
                               plot_best: bool = False,
                               save_results: bool = True,
                               save_pdf=True,
                               results_file: str = 'backtest_results.json') -> pd.DataFrame:
        """
        Run multiple strategies and compare results
        
        Args:
            strategy_names: List of strategy names to run
            data_feed: Backtrader data feed
            plot_best: Whether to plot the best performing strategy
            save_results: Whether to save results to file
            results_file: Filename for results
        
        Returns:
            DataFrame with comparison of all strategies
        """
        results = []
        
        print(f"\n{'='*60}")
        print(f"Running {len(strategy_names)} strategies for comparison")
        print(f"{'='*60}")
        
        for strategy_name in strategy_names:
            print(f"\n{'-'*60}")
            print(f"Testing Strategy: {strategy_name.upper()}")
            print(f"{'-'*60}")
            
            # Get strategy config and create class
            config = get_strategy_config(strategy_name)
            if not config:
                print(f"Strategy '{strategy_name}' not found. Skipping...")
                continue
            
            strategy_class = create_strategy_from_config(config)
            
            # Run strategy
            result = self.run_strategy(
                strategy_class=strategy_class,
                data_feed=data_feed,
                plot=False,
                verbose=True
            )
            
            result['strategy_name'] = strategy_name
            results.append(result)
        
        # Create comparison DataFrame
        df_results = pd.DataFrame(results)
        
        # Sort by total return
        df_results = df_results.sort_values('total_return_pct', ascending=False)
        
        # Display comparison
        self._display_comparison(df_results)
        
        # Save results
        if save_results:
            self._save_results(results, results_file)
        
        # Plot best strategy
        if plot_best and len(results) > 0:
            best_strategy_name = df_results.iloc[0]['strategy_name']
            print(f"\n Plotting best strategy: {best_strategy_name}")
            
            config = get_strategy_config(best_strategy_name)
            strategy_class = create_strategy_from_config(config)
            self.run_strategy(
                strategy_class=strategy_class,
                data_feed=data_feed,
                plot=True,
                verbose=False
            )
        
        return df_results
    
    def _collect_results(self, 
                        strategy, 
                        start_value: float, 
                        end_value: float,
                        verbose: bool = True) -> Dict[str, Any]:
        """Collect and calculate all performance metrics"""
        
        # Basic metrics
        gross_return = end_value - start_value
        total_return_pct = (gross_return / start_value) * 100
        
        # Get strategy-specific metrics
        perf_metrics = strategy.get_performance_metrics()
        
        # Calculate annualized return
        days_traded = perf_metrics['days_traded']
        if days_traded > 0:
            annualized_return = ((end_value / start_value) ** (365 / days_traded)) - 1
            annualized_return_pct = annualized_return * 100
        else:
            annualized_return_pct = 0
        
        # Get analyzer results
        sharpe = strategy.analyzers.sharpe.get_analysis()
        drawdown = strategy.analyzers.drawdown.get_analysis()
        returns = strategy.analyzers.returns.get_analysis()
        trades = strategy.analyzers.trades.get_analysis()
        
        # Build result dictionary
        result = {
            'start_value': start_value,
            'end_value': end_value,
            'gross_return': gross_return,
            'total_return_pct': total_return_pct,
            'annualized_return_pct': annualized_return_pct,
            'sharpe_ratio': sharpe.get('sharperatio', None),
            'max_drawdown': drawdown.max.drawdown,
            'max_drawdown_pct': drawdown.max.drawdown / start_value * 100 if start_value > 0 else 0,
            'total_trades': perf_metrics['total_trades'],
            'winning_trades': perf_metrics['winning_trades'],
            'losing_trades': perf_metrics['losing_trades'],
            'win_rate': perf_metrics['win_rate'],
            'profit_factor': perf_metrics['profit_factor'],
            'avg_win': perf_metrics['avg_win'],
            'avg_loss': perf_metrics['avg_loss'],
            'days_traded': days_traded,
            'trade_journal': strategy.trade_journal
        }
        
        if verbose:
            print(f"\n{'='*60}")
            print("PERFORMANCE SUMMARY")
            print(f"{'='*60}")
            print(f"Gross Return: ₹{gross_return:,.2f} ({total_return_pct:.2f}%)")
            print(f"Annualized Return: {annualized_return_pct:.2f}%")
            print(f"Sharpe Ratio: {result['sharpe_ratio']}")
            print(f"Max Drawdown: {result['max_drawdown_pct']:.2f}%")
            print(f"Total Trades: {result['total_trades']}")
            print(f"Win Rate: {result['win_rate']:.2f}%")
            print(f"Profit Factor: {result['profit_factor']:.2f}")
            print(f"Days in Market: {days_traded}")
            print(f"{'='*60}\n")
        
        return result
    
    def _display_comparison(self, df: pd.DataFrame):
        """Display comparison table of strategies"""
        print(f"\n{'='*80}")
        print("STRATEGY COMPARISON")
        print(f"{'='*80}")
        
        # Select key columns for display
        display_cols = [
            'strategy_name',
            'total_return_pct',
            'annualized_return_pct',
            'sharpe_ratio',
            'max_drawdown_pct',
            'win_rate',
            'total_trades',
            'profit_factor'
        ]
        
        # Create display dataframe
        df_display = df[display_cols].copy()
        df_display.columns = [
            'Strategy',
            'Return %',
            'Ann. Return %',
            'Sharpe',
            'Max DD %',
            'Win Rate %',
            'Trades',
            'Profit Factor'
        ]
        
        print(df_display.to_string(index=False))
        print(f"{'='*80}\n")
    
    def _save_results(self, results: List[Dict], filename: str):
        """Save results to JSON file"""
        # Convert trade journals to serializable format
        for result in results:
            if 'trade_journal' in result:
                result['trade_journal'] = [
                    {k: str(v) if isinstance(v, datetime) else v 
                     for k, v in trade.items()}
                    for trade in result['trade_journal']
                ]
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to {filename}")


def run_backtest(stock_code: str,
                 strategy_name: str,
                 data_loader_func,
                 years: int = 5,
                 initial_cash: Optional[float] = None,  # ← Changed
                 normalized_mode: bool = False,  # ← New parameter
                 plot: bool = True,
                 enhanced_plot: bool = True,
                 **strategy_params):
    """
    Convenience function to run a single backtest
    
    Args:
        stock_code: Stock ticker symbol
        strategy_name: Name of strategy to run
        data_loader_func: Function to load price data
        years: Number of years of historical data
        initial_cash: Starting cash (if None, uses normalized mode)
        normalized_mode: If True, returns only percentage metrics
        plot: Whether to plot results
        enhanced_plot: Whether to use enhanced visualizations (default: True)
        **strategy_params: Additional strategy parameters
    
    Returns:
        Results dictionary
    """
    # Load data
    df, dates, cols = data_loader_func(stock_code, years=years)
    feed = bt.feeds.PandasData(dataname=df)
    
    # Get strategy
    config = get_strategy_config(strategy_name)
    if not config:
        raise ValueError(f"Strategy '{strategy_name}' not found")
    
    strategy_class = create_strategy_from_config(config)
    
    # Run backtest
    if normalized_mode or initial_cash is None:
        engine = BacktestEngine(normalized_mode=True)  # ← Uses default 100k
    else:
        engine = BacktestEngine(initial_cash=initial_cash)
        
    results = engine.run_strategy(
        strategy_class=strategy_class,
        data_feed=feed,
        strategy_params=strategy_params,
        plot=plot,
        enhanced_plot=enhanced_plot,
        verbose=True
    )
    return results



def compare_strategies(stock_code: str,
                      strategy_names: List[str],
                      data_loader_func,
                      years: int = 5,
                      initial_cash: Optional[float] = None,  # ← Changed
                      normalized_mode: bool = False,  # ← New
                      plot_best: bool = True,
                      save_results: bool = True):
    """
    Convenience function to compare multiple strategies
    
    Args:
        stock_code: Stock ticker symbol
        strategy_names: List of strategy names to compare
        data_loader_func: Function to load price data
        years: Number of years of historical data
        initial_cash: Starting cash (if None, uses normalized mode)
        normalized_mode: If True, focuses on percentage returns
        plot_best: Whether to plot best strategy
        save_results: Whether to save results
    
    Returns:
        DataFrame with comparison results
    """
    # Load data
    df, dates, cols = data_loader_func(stock_code, years=years)
    feed = bt.feeds.PandasData(dataname=df)
    
    # Run comparison
    if normalized_mode or initial_cash is None:
        engine = BacktestEngine(normalized_mode=True)
    else:
        engine = BacktestEngine(initial_cash=initial_cash)
        
    results_df = engine.run_multiple_strategies(
        strategy_names=strategy_names,
        data_feed=feed,
        plot_best=plot_best,
        save_results=save_results,
        results_file=f'{stock_code}_comparison.json'
    )
    
    return results_df










