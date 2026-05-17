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
from analysis_scripts.utils.primary_indicators import (
    add_indicators
)
from analysis_scripts.utils.advanced_indicators import (
    add_advanced_indicators
)
from research_indicators.strategies_util.custom_data_feed import ExtendedPandasData








def run_one_stock_one_strategy(
    strategies,
    strategy_name="SMA200_RSI_Strategy",
    stock="TCS",
    base_path_prefix="research_indicators/strategy_reports",
    my_ind=False,
    YRS=3,
    logger=None,
):
    if logger is None:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s -> %(message)s",
            handlers=[logging.FileHandler(f"logs/{strategy_name}_strategy.log"), logging.StreamHandler()],
        )
        logger = logging.getLogger(__name__)

    print("\n" + "=" * 80)
    print(f"{strategy_name} Strategy")
    print("=" * 80)

    # Load data
    df, dates, cols = load_prices(stock, years=YRS)
    if df is None:
        logger.error(f"Stock {stock} is not found")
        return

    if my_ind:
        df = add_indicators(df)
        df = add_advanced_indicators(df)
        # print(df.columns)
        feed = ExtendedPandasData(dataname=df)
    else:
        feed = bt.feeds.PandasData(dataname=df)

    strategy = strategies.get(strategy_name, None)
    if strategy is None:
        raise ValueError(f"No Strategy Found")

    # Run backtest
    engine = BacktestEngine(initial_cash=100000)
    results = engine.run_strategy(
        strategy_class=strategy,
        data_feed=feed,
        plot=False,
        enhanced_plot=True,
        save_prefix=f"{stock}",
        base_path=f"{base_path_prefix}/{strategy_name}",
        verbose=True,
    )

    print(f"\n{strategy_name} Strategy Results:")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    return results





def run_multiple_stocks_one_strategy(
    strategies,
    strategy_name="SMA200_RSI_Strategy",
    stocks=["TCS", "INFY", "WIPRO"],
    base_path_prefix="research_indicators/strategy_reports",
    my_ind=False,
    YRS=3,
    logger=None,
):
    if logger is None:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(f"logs/{strategy_name}_strategy.log"), logging.StreamHandler()],
        )
        logger = logging.getLogger(__name__)

    strategy = strategies.get(strategy_name, None)
    if strategy is None:
        raise ValueError(f"No Strategy Found")

    # Run backtest
    engine = BacktestEngine(initial_cash=100000)

    results_summary = []

    for stock in stocks:
        print(f"\n{'-'*60}")
        print(f"Testing {stock}")
        print(f"{'-'*60}")

        # Load data
        df, dates, cols = load_prices(stock, years=YRS)
        if df is None:
            logger.error(f"Stock {stock} is not found")
            continue
        if my_ind:
            df = add_indicators(df)
            df = add_advanced_indicators(df)
            # logger.info(df.columns)
            feed = ExtendedPandasData(dataname=df)
        else:
            feed = bt.feeds.PandasData(dataname=df)

        try:
            results = engine.run_strategy(
                strategy_class=strategy,
                data_feed=feed,
                plot=False,
                enhanced_plot=True,
                save_prefix=f"{stock}",
                base_path=f"{base_path_prefix}/{strategy_name}",
                verbose=True,
            )

            results_summary.append(
                {
                    "stock": stock,
                    "return_pct": results["total_return_pct"],
                    "sharpe": results["sharpe_ratio"],
                    "win_rate": results["win_rate"],
                    "total_trades": results["total_trades"],
                }
            )

        except Exception as e:
            print(f"Error testing {stock}: {e}")
            continue

    # Display summary
    import pandas as pd

    df_summary = pd.DataFrame(results_summary)
    df_summary = df_summary.sort_values("return_pct", ascending=False)

    df_summary.to_csv(f"{base_path_prefix}/summary_{strategy_name}.csv", index=False)

    print("\n" + "=" * 80)
    print("MULTI-STOCK SUMMARY")
    print("=" * 80)
    print(df_summary.to_string(index=False))
    return df_summary

