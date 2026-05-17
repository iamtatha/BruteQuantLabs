"""
Strategy Configurations Module
Define trading strategies as simple dictionaries with conditions
"""

import backtrader as bt
from typing import Dict, Any, Callable, Optional
import datetime


class StrategyConfig:
    """
    Configuration class for defining trading strategies
    """
    
    def __init__(self, name: str, logger):
        self.name = name
        self.logger = logger
        self.indicators = {}
        self.buy_conditions = []
        self.sell_conditions = []
        self.params = {}
        
    def add_indicator(self, name: str, indicator: Any, **kwargs):
        """Add an indicator to the strategy"""
        self.indicators[name] = {'indicator': indicator, 'params': kwargs}
        return self
    
    def add_buy_condition(self, condition: Callable):
        """Add a buy condition (function that returns bool)"""
        self.buy_conditions.append(condition)
        return self
    
    def add_sell_condition(self, condition: Callable):
        """Add a sell condition (function that returns bool)"""
        self.sell_conditions.append(condition)
        return self
    
    def set_params(self, **kwargs):
        """Set strategy parameters"""
        self.params.update(kwargs)
        return self


# Pre-defined strategy configurations
def get_bollinger_band_strategy() -> StrategyConfig:
    """
    Bollinger Band Strategy Configuration
    
    Buy: Price > 200 SMA AND Price < Lower Bollinger Band
    Sell: 10 days holding OR RSI > 50
    """
    config = StrategyConfig("BollingerBand")
    
    # Define indicators
    config.add_indicator('sma_200', bt.ind.SMA, period=200)
    config.add_indicator('bollinger', bt.ind.BollingerBands, period=20, devfactor=2.5)
    config.add_indicator('rsi', bt.indicators.RSI, period=2, safediv=True)
    
    # Buy conditions
    def buy_condition(strategy):
        return (strategy.dataclose[0] > strategy.sma_200[0] and 
                strategy.dataclose[0] < strategy.bollinger.lines.bot[0])
    
    config.add_buy_condition(buy_condition)
    
    # Sell conditions
    def sell_condition(strategy):
        days_held = len(strategy) - strategy.bar_executed
        return days_held >= 10 or strategy.rsi[0] > 50
    
    config.add_sell_condition(sell_condition)
    
    # Strategy parameters
    config.set_params(
        limit_order_discount=0.97,  # Buy at 3% discount
        position_size_pct=0.95      # Use 95% of available cash
    )
    
    return config


def get_stochastic_strategy() -> StrategyConfig:
    """
    Stochastic Oscillator Strategy Configuration
    
    Buy: Price > 200 SMA AND Stochastic K <= 5
    Sell: 10 days holding OR Price > Buy Price
    """
    config = StrategyConfig("Stochastic")
    
    # Define indicators
    config.add_indicator('sma_200', bt.ind.SMA, period=200)
    config.add_indicator('stochastic', bt.ind.Stochastic, period=10, period_dfast=1, period_dslow=1)
    
    # Buy conditions
    def buy_condition(strategy):
        return (strategy.dataclose[0] > strategy.sma_200[0] and 
                strategy.stochastic.percK[0] <= 5)
    
    config.add_buy_condition(buy_condition)
    
    # Sell conditions
    def sell_condition(strategy):
        days_held = len(strategy) - strategy.bar_executed
        return days_held >= 10 or strategy.dataclose[0] > strategy.target_price
    
    config.add_sell_condition(sell_condition)
    
    # Strategy parameters
    config.set_params(
        limit_order_discount=0.97,
        position_size_pct=0.95,
        limit_order_valid_days=5
    )
    
    return config


def get_rsi_strategy() -> StrategyConfig:
    """
    RSI Mean Reversion Strategy
    
    Buy: RSI < 30 (oversold)
    Sell: RSI > 70 (overbought) OR 5% profit target
    """
    config = StrategyConfig("RSI_MeanReversion")
    
    config.add_indicator('rsi', bt.indicators.RSI, period=14, safediv=True)
    config.add_indicator('sma_50', bt.ind.SMA, period=50)
    
    def buy_condition(strategy):
        return (strategy.rsi[0] < 30 and 
                strategy.dataclose[0] > strategy.sma_50[0])
    
    def sell_condition(strategy):
        if strategy.buy_price:
            profit_pct = ((strategy.dataclose[0] - strategy.buy_price) / strategy.buy_price) * 100
            return strategy.rsi[0] > 70 or profit_pct >= 5
        return strategy.rsi[0] > 70
    
    config.add_buy_condition(buy_condition)
    config.add_sell_condition(sell_condition)
    config.set_params(position_size_pct=0.95)
    
    return config


def get_moving_average_crossover_strategy() -> StrategyConfig:
    """
    Moving Average Crossover Strategy
    
    Buy: Fast SMA crosses above Slow SMA (Golden Cross)
    Sell: Fast SMA crosses below Slow SMA (Death Cross) OR 3% stop loss
    """
    config = StrategyConfig("MA_Crossover")
    
    config.add_indicator('sma_fast', bt.ind.SMA, period=50)
    config.add_indicator('sma_slow', bt.ind.SMA, period=200)
    
    def buy_condition(strategy):
        # Golden cross: fast crosses above slow
        return (strategy.sma_fast[0] > strategy.sma_slow[0] and 
                strategy.sma_fast[-1] <= strategy.sma_slow[-1])
    
    def sell_condition(strategy):
        # Death cross or stop loss
        death_cross = (strategy.sma_fast[0] < strategy.sma_slow[0] and 
                      strategy.sma_fast[-1] >= strategy.sma_slow[-1])
        
        stop_loss = False
        if strategy.buy_price:
            loss_pct = ((strategy.dataclose[0] - strategy.buy_price) / strategy.buy_price) * 100
            stop_loss = loss_pct <= -3
        
        return death_cross or stop_loss
    
    config.add_buy_condition(buy_condition)
    config.add_sell_condition(sell_condition)
    config.set_params(position_size_pct=0.95)
    
    return config


def get_breakout_strategy() -> StrategyConfig:
    """
    Breakout Strategy
    
    Buy: Price breaks above 20-day high with volume confirmation
    Sell: Price falls below 10-day low OR 10% profit target
    """
    config = StrategyConfig("Breakout")
    
    config.add_indicator('highest', bt.ind.Highest, period=20, subplot=False)
    config.add_indicator('lowest', bt.ind.Lowest, period=10, subplot=False)
    config.add_indicator('sma_volume', bt.ind.SMA, period=20, subplot=True)
    
    def buy_condition(strategy):
        # Breakout above 20-day high with volume > average
        return (strategy.dataclose[0] > strategy.highest[-1] and 
                strategy.datas[0].volume[0] > strategy.sma_volume[0])
    
    def sell_condition(strategy):
        # Stop loss at 10-day low or 10% profit
        stop_loss = strategy.dataclose[0] < strategy.lowest[0]
        
        take_profit = False
        if strategy.buy_price:
            profit_pct = ((strategy.dataclose[0] - strategy.buy_price) / strategy.buy_price) * 100
            take_profit = profit_pct >= 10
        
        return stop_loss or take_profit
    
    config.add_buy_condition(buy_condition)
    config.add_sell_condition(sell_condition)
    config.set_params(position_size_pct=0.95)
    
    return config


def get_macd_strategy() -> StrategyConfig:
    """
    MACD Strategy
    
    Buy: MACD line crosses above signal line AND histogram > 0
    Sell: MACD line crosses below signal line OR 5 days holding
    """
    config = StrategyConfig("MACD")
    
    config.add_indicator('macd', bt.ind.MACD, 
                        period_me1=12, period_me2=26, period_signal=9)
    config.add_indicator('sma_200', bt.ind.SMA, period=200)
    
    def buy_condition(strategy):
        macd_cross = (strategy.macd.macd[0] > strategy.macd.signal[0] and 
                     strategy.macd.macd[-1] <= strategy.macd.signal[-1])
        trend_filter = strategy.dataclose[0] > strategy.sma_200[0]
        return macd_cross and trend_filter
    
    def sell_condition(strategy):
        macd_cross_down = (strategy.macd.macd[0] < strategy.macd.signal[0] and 
                          strategy.macd.macd[-1] >= strategy.macd.signal[-1])
        
        days_held = len(strategy) - strategy.bar_executed
        time_exit = days_held >= 5
        
        return macd_cross_down or time_exit
    
    config.add_buy_condition(buy_condition)
    config.add_sell_condition(sell_condition)
    config.set_params(position_size_pct=0.95)
    
    return config


# Registry of all available strategies
STRATEGY_REGISTRY = {
    'bollinger': get_bollinger_band_strategy,
    'stochastic': get_stochastic_strategy,
    'rsi': get_rsi_strategy,
    'ma_crossover': get_moving_average_crossover_strategy,
    'breakout': get_breakout_strategy,
    'macd': get_macd_strategy,
}


def get_strategy_config(strategy_name: str) -> Optional[StrategyConfig]:
    """
    Get a strategy configuration by name
    
    Args:
        strategy_name: Name of the strategy (key in STRATEGY_REGISTRY)
    
    Returns:
        StrategyConfig object or None if not found
    """
    factory = STRATEGY_REGISTRY.get(strategy_name.lower())
    if factory:
        return factory()
    return None


def list_available_strategies() -> list:
    """Return list of available strategy names"""
    return list(STRATEGY_REGISTRY.keys())
