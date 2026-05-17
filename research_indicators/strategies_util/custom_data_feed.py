"""
Custom Pandas Data Feed
Allows access to pre-calculated indicators from DataFrame
"""

import backtrader as bt


class ExtendedPandasData(bt.feeds.PandasData):
    """
    Extended Pandas Data Feed that exposes all DataFrame columns as lines
    
    This allows you to access pre-calculated indicators like:
    - df['rsi'] → self.rsi[0]
    - df['sma_200'] → self.sma_200[0]
    - df['supertrend_upper'] → self.supertrend_upper[0]
    """
    
    # Add all your indicator columns as lines
    lines = (
        'sma_20', 'sma_50', 'sma_200', 'sma_volume', 'ema_20', 'ema_7', 'ema_33', 'vwap',
        'rsi', 'macd', 'macd_signal', 'macd_hist', 'roc_12',
        'stoch_k', 'stoch_d', 'obv', 'mfi', 'ad_line', 'atr',
        'bb_middle', 'bb_upper', 'bb_lower',
        'pivot', 'r1', 's1',
        'fib_0_236', 'fib_0_382', 'fib_0_5', 'fib_0_618',
        'tenkan', 'kijun', 'senkou_a', 'senkou_b', 'chikou',
        'aroon_up', 'aroon_down', 'vortex_plus', 'vortex_minus',
        'supertrend_upper', 'supertrend_lower', 'supertrend', 'supertrend_direction',
        'williams_r', 'stoch_rsi', 'trix', 'cci', 'cmf', 'vol_osc',
        'kc_upper', 'kc_lower', 'donchian_upper', 'donchian_lower',
        'hma', 'kama',
    )
    
    # Map DataFrame columns to lines
    params = (
        ('sma_20', -1),
        ('sma_50', -1),
        ('sma_200', -1),
        ('sma_volume', -1),
        ('ema_20', -1),
        ('ema_7', -1),
        ('ema_33', -1),
        ('vwap', -1),
        ('rsi', -1),
        ('macd', -1),
        ('macd_signal', -1),
        ('macd_hist', -1),
        ('roc_12', -1),
        ('stoch_k', -1),
        ('stoch_d', -1),
        ('obv', -1),
        ('mfi', -1),
        ('ad_line', -1),
        ('atr', -1),
        ('bb_middle', -1),
        ('bb_upper', -1),
        ('bb_lower', -1),
        ('pivot', -1),
        ('r1', -1),
        ('s1', -1),
        ('fib_0_236', -1),
        ('fib_0_382', -1),
        ('fib_0_5', -1),
        ('fib_0_618', -1),
        ('tenkan', -1),
        ('kijun', -1),
        ('senkou_a', -1),
        ('senkou_b', -1),
        ('chikou', -1),
        ('aroon_up', -1),
        ('aroon_down', -1),
        ('vortex_plus', -1),
        ('vortex_minus', -1),
        ('supertrend_upper', -1),
        ('supertrend_lower', -1),
        ('supertrend', -1),
        ('supertrend_direction', -1),
        ('williams_r', -1),
        ('stoch_rsi', -1),
        ('trix', -1),
        ('cci', -1),
        ('cmf', -1),
        ('vol_osc', -1),
        ('kc_upper', -1),
        ('kc_lower', -1),
        ('donchian_upper', -1),
        ('donchian_lower', -1),
        ('hma', -1),
        ('kama', -1),
    )


