import sys
from pathlib import Path

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import logging
import backtrader as bt
from utils.dataloader import load_prices, load_industry, load_stock_codes_industries

from research_indicators.strategies_util.backtest_engine import (
    BacktestEngine,
    run_backtest,
    compare_strategies,
)
from research_indicators.strategies_util.strategy_configs import (
    list_available_strategies,
    get_strategy_config,
)
from research_indicators.strategies_util.strategy_factory import (
    create_strategy_from_config,
    create_custom_strategy,
)
from research_indicators.run_strategies_helper import (
    run_one_stock_one_strategy,
    run_multiple_stocks_one_strategy,
)
from research_indicators.strategies_util.custom_data_feed import ExtendedPandasData

# Setup logging

import logging
import os

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("my_logger")

logger.setLevel(logging.INFO)

# IMPORTANT
logger.propagate = False

# Remove old handlers
logger.handlers.clear()

# File handler
fh = logging.FileHandler(
    "logs/SUPERTREND_RSI_strategies.log",
    encoding="utf-8"
)

# Console handler
sh = logging.StreamHandler()

formatter = logging.Formatter(
    "%(asctime)s -> %(message)s"
)

fh.setFormatter(formatter)
sh.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(sh)





def load_strategies():
    CustomStrategy = create_custom_strategy(
        name="BULL_BEAR_FLAG",
        logger=logger,
        indicators={
            "atr": (bt.ind.ATR, {"period": 14}),
            "volume_sma": (bt.ind.SMA, {"period": 20, "plot": False}),  # 20-day avg volume
        },
        buy_conditions=[
            # Strong trend move (pole): 10%+ move in recent 5 days
            lambda s: len(s) > 5 and ((s.dataclose[0] - s.dataclose[-5]) / s.dataclose[-5]) >= 0.10,
            
            # Consolidation: price near recent 10-day high
            lambda s: len(s) > 10 and s.dataclose[0] >= max([s.dataclose[-i] for i in range(10)]) * 0.95,
            
            # Flag retracement: 38-50% of the pole move
            lambda s: (
                len(s) > 10 and
                (lambda pole_high, pole_low, recent_low: (
                    pole_high > pole_low and
                    recent_low > 0 and
                    0.38 <= (pole_high - recent_low) / (pole_high - pole_low) <= 0.50
                ))(
                    s.dataclose[-5],  # pole_high
                    min([s.dataclose[-i] for i in range(5, 11)]),  # pole_low (6-10 days ago)
                    min([s.dataclose[-i] for i in range(10)])  # recent_low
                )
            ),
            
            # Volume spike on breakout: 2x average volume
            lambda s: s.data.volume[0] >= 2.0 * s.data.sma_volume[0],
            
            # Breakout above flag resistance (recent 10-day high)
            lambda s: len(s) > 10 and s.dataclose[0] > max([s.dataclose[-i] for i in range(1, 11)]),
        ],
        sell_conditions=[
            # Bearish reversal: Strong downtrend
            lambda s: (
                len(s) > 10 and
                ((s.dataclose[0] - s.dataclose[-5]) / s.dataclose[-5]) <= -0.10 and
                s.dataclose[0] < min([s.dataclose[-i] for i in range(10)]) * 1.05
            ),
            
            # STOP LOSS: -4%
            lambda s: s.buy_price and ((s.dataclose[0] - s.buy_price) / s.buy_price) <= -0.04,
            
            # TAKE PROFIT: 10% (pole height)
            lambda s: s.buy_price and ((s.dataclose[0] - s.buy_price) / s.buy_price) >= 0.10,
        ],
        position_size_pct=1.0,
    )

    global strategies
    strategies = {"BULL_BEAR_FLAG": CustomStrategy}



YRS = 3

# _, stock_list = load_industry()
stock_list, _ = load_stock_codes_industries(v=500)
# print(stock_list)


load_strategies()

# run_one_strategy()
# run_multiple(strategy_name="RSI_SUPERTREND_R1", stocks=stock_list)



# run_one_stock_one_strategy(
#     strategies,
#     strategy_name="BULL_BEAR_FLAG",
#     base_path_prefix="research_indicators/strategy_reports",
#     my_ind=True,
#     YRS=3,
#     logger=logger,
# )


run_multiple_stocks_one_strategy(
    strategies,
    strategy_name="BULL_BEAR_FLAG",
    stocks=stock_list,
    base_path_prefix="research_indicators/strategy_reports",
    my_ind=True,
    YRS=3,
    logger=logger,
)

