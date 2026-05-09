"""
Dynamic Strategy Factory
Creates strategy classes dynamically from StrategyConfig objects
"""

import backtrader as bt
from research_indicators.strategies_util.base_strategy import BaseStrategy
from research_indicators.strategies_util.strategy_configs import StrategyConfig
import math
import datetime


def create_strategy_from_config(config: StrategyConfig):
    """
    Dynamically create a strategy class from a StrategyConfig
    
    Args:
        config: StrategyConfig object defining the strategy
    
    Returns:
        A strategy class that inherits from BaseStrategy
    """
    
    class DynamicStrategy(BaseStrategy):
        """Dynamically created strategy based on configuration"""
        
        params = tuple(config.params.items())
        
        def __init__(self):
            super().__init__()
            
            # Store configuration
            self.config = config
            self.strategy_name = config.name
            
            # Initialize indicators from config
            for name, ind_config in config.indicators.items():
                indicator_class = ind_config['indicator']
                params = ind_config['params']
                
                # Create indicator and attach it to strategy
                setattr(self, name, indicator_class(self.datas[0], **params))
            
            # Store target price for limit orders (used in some strategies)
            self.target_price = None
        
        def buy_signal(self) -> bool:
            """Evaluate all buy conditions"""
            if not config.buy_conditions:
                return False
            
            # All conditions must be True
            return all(condition(self) for condition in config.buy_conditions)
        
        def sell_signal(self) -> bool:
            """Evaluate all sell conditions"""
            if not config.sell_conditions:
                return False
            
            # Any condition can be True
            return any(condition(self) for condition in config.sell_conditions)
        
        def execute_buy(self):
            """Execute buy order with custom logic based on params"""
            # Get parameters
            limit_discount = getattr(self.p, 'limit_order_discount', None)
            position_size_pct = getattr(self.p, 'position_size_pct', 0.95)
            valid_days = getattr(self.p, 'limit_order_valid_days', None)
            
            current_price = self.dataclose[0]
            
            # Calculate target price if using limit orders
            if limit_discount:
                target_price = current_price * limit_discount
                self.target_price = target_price
            else:
                target_price = current_price
            
            # Calculate position size
            qty = self.calculate_position_size(target_price, position_size_pct)
            
            if qty > 0:
                self.log(f'BUY CREATE, Price: {current_price:.2f}, '
                        f'Target: {target_price:.2f}, Qty: {qty}')
                
                # Create order with appropriate parameters
                order_kwargs = {
                    'size': qty
                }
                
                if limit_discount:
                    order_kwargs['exectype'] = bt.Order.Limit
                    order_kwargs['price'] = target_price
                    
                    if valid_days:
                        order_kwargs['valid'] = datetime.timedelta(days=valid_days)
                
                self.order = self.buy(**order_kwargs)
                self.qty_sell_track = 0
                self.log_buy = 0
    
    # Set a readable name for the class
    DynamicStrategy.__name__ = f"{config.name}Strategy"
    
    return DynamicStrategy


def create_custom_strategy(name: str, 
                          indicators: dict,
                          buy_conditions: list,
                          sell_conditions: list,
                          **params):
    """
    Quick way to create a custom strategy without explicitly creating a StrategyConfig
    
    Args:
        name: Strategy name
        indicators: Dict of {name: (indicator_class, params_dict)}
        buy_conditions: List of condition functions
        sell_conditions: List of condition functions
        **params: Strategy parameters
    
    Returns:
        Strategy class
    
    Example:
        >>> strategy = create_custom_strategy(
        ...     name="MyStrategy",
        ...     indicators={
        ...         'sma': (bt.ind.SMA, {'period': 20}),
        ...         'rsi': (bt.ind.RSI, {'period': 14})
        ...     },
        ...     buy_conditions=[
        ...         lambda s: s.dataclose[0] > s.sma[0],
        ...         lambda s: s.rsi[0] < 30
        ...     ],
        ...     sell_conditions=[
        ...         lambda s: s.rsi[0] > 70
        ...     ],
        ...     position_size_pct=0.95
        ... )
    """
    config = StrategyConfig(name)
    
    # Add indicators
    for ind_name, (ind_class, ind_params) in indicators.items():
        config.add_indicator(ind_name, ind_class, **ind_params)
    
    # Add conditions
    for condition in buy_conditions:
        config.add_buy_condition(condition)
    
    for condition in sell_conditions:
        config.add_sell_condition(condition)
    
    # Set parameters
    config.set_params(**params)
    
    return create_strategy_from_config(config)
