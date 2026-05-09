import sys
from pathlib import Path

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import logging
import backtrader as bt
from utils.dataloader import load_prices

from research_indicators.strategies_util.backtest_engine import (
    BacktestEngine, 
    run_backtest, 
    compare_strategies
)
from research_indicators.strategies_util.strategy_configs import (
    list_available_strategies,
    get_strategy_config
)
from research_indicators.strategies_util.strategy_factory import (
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



def load_strategies():
    CustomStrategy = create_custom_strategy(
        name="SMA200_RSI_Strategy",
        indicators={
            'sma_200': (bt.ind.SMA, {'period': 200}),
            'rsi': (bt.ind.RSI, {'period': 14, 'safediv': True})
        },
        buy_conditions=[
            lambda s: s.dataclose[0] > s.sma_200[0],  # Price above SMA 200
            lambda s: s.rsi[0] < 30  # RSI oversold
        ],
        sell_conditions=[
            lambda s: s.rsi[0] > 40,  # RSI exits oversold zone
            lambda s: len(s) - s.bar_executed >= 10  # Held for 10 days
        ],
        position_size_pct=1.0  # Use 100% of available cash
    )
    
    global strategies 
    strategies = {
        "SMA200_RSI_Strategy": CustomStrategy
    }



def run_one_strategy(strategy_name="SMA200_RSI_Strategy", stocks=["TCS"]):
    print("\n" + "="*80)
    print("RAYNER TEO: SMA 200 + RSI Strategy")
    print("="*80)
    

    # Load data
    df, dates, cols = load_prices('TCS', years=5)
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
        verbose=True
    )
    
    print(f"\nSMA200 + RSI Strategy Results:")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Win Rate: {results['win_rate']:.2f}%")




# def run_multiple(strategy_name="SMA200_RSI_Strategy"):
#     stocks = ['TCS', 'INFY', 'WIPRO', 'HCLTECH']
    
#     results_summary = []
    
#     for stock in stocks:
#         print(f"\n{'-'*60}")
#         print(f"Testing {stock}")
#         print(f"{'-'*60}")
        
#         try:
#             results = run_backtest(
#                 stock_code=stock,
#                 strategy_name=strategy_name,
#                 data_loader_func=load_prices,
#                 years=3,
#                 initial_cash=100000,
#                 plot=False
#             )
            
#             results_summary.append({
#                 'stock': stock,
#                 'return_pct': results['total_return_pct'],
#                 'sharpe': results['sharpe_ratio'],
#                 'win_rate': results['win_rate'],
#                 'total_trades': results['total_trades']
#             })
            
#         except Exception as e:
#             print(f"Error testing {stock}: {e}")
#             continue
    
#     # Display summary
#     import pandas as pd
#     df_summary = pd.DataFrame(results_summary)
#     df_summary = df_summary.sort_values('return_pct', ascending=False)
    
#     print("\n" + "="*80)
#     print("MULTI-STOCK SUMMARY")
#     print("="*80)
#     print(df_summary.to_string(index=False))






load_strategies()
run_one_strategy()
# run_multiple()





