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
        name="SUPERTREND_RSI",
        logger=logger,
        indicators={
            "sma_200": (bt.ind.SMA, {"period": 200}),
            "rsi": (bt.ind.RSI, {"period": 14, "safediv": True}),
        },
        buy_conditions=[
            lambda s: s.data.supertrend_direction[0] == 1,  
            lambda s: s.data.rsi[0] < 30,
            # lambda s: s.data.close[0] > s.data.r1[0],
        ],
        sell_conditions=[
            lambda s: s.data.rsi[0] > 40,
            lambda s: s.data.supertrend_direction[0] == -1,
            # STOP LOSS: Exit if price drops 3% below buy price
            lambda s: s.buy_price
            and ((s.dataclose[0] - s.buy_price) / s.buy_price) <= -0.05,
            # TAKE PROFIT: +5%
            lambda s: s.buy_price
            and ((s.dataclose[0] - s.buy_price) / s.buy_price) >= 0.1,
        ],
        position_size_pct=1.0,  # Use 100% of available cash
    )

    global strategies
    strategies = {"SUPERTREND_RSI": CustomStrategy}



YRS = 3

# _, stock_list = load_industry()
stock_list, _ = load_stock_codes_industries(v=500)
# print(stock_list)


load_strategies()

# run_one_strategy()
# run_multiple(strategy_name="RSI_SUPERTREND_R1", stocks=stock_list)



# run_one_stock_one_strategy(
#     strategies,
#     strategy_name="SUPERTREND_RSI",
#     base_path_prefix="research_indicators/strategy_reports",
#     my_ind=True,
#     YRS=3,
#     logger=logger,
# )


run_multiple_stocks_one_strategy(
    strategies,
    strategy_name="SUPERTREND_RSI",
    stocks=stock_list,
    base_path_prefix="research_indicators/strategy_reports",
    my_ind=True,
    YRS=3,
    logger=logger,
)

