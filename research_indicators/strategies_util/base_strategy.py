"""
Base Strategy Class for Backtesting Framework
All trading strategies should inherit from this class
"""

import backtrader as bt
import math
from typing import Dict, List, Any, Optional


class BaseStrategy(bt.Strategy):
    """
    Base class for all trading strategies.
    Provides common functionality like logging, trade journal, and order management.
    """
    
    params = (
        ('printlog', True),
    )
    
    def __init__(self):
        """Initialize common indicators and tracking variables"""
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # To keep track of pending orders
        self.order = None
        self.buy_price = None
        self.buy_size = None
        
        # Trade tracking
        self.qty_sell_track = 0
        self.log_buy = 0
        self.log_sell = 0
        self.times_traded = 0
        self.days_traded = 0
        self.trade_journal = []
        
        # Performance metrics
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0
        self.total_loss = 0
        
    def log(self, txt: str, dt=None, do_print: bool = None) -> Any:
        """Logging function for this strategy"""
        if do_print is None:
            do_print = self.params.printlog
            
        if do_print:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')
        return dt
    
    def add_to_journal(self, order: bt.Order):
        """Add trade to journal with detailed metrics"""
        dt = self.datas[0].datetime.date(0)
        
        if order.isbuy():
            self.trade_journal.append({
                "date": dt,
                "type": "buy",
                "price": order.executed.price,
                "size": self.position.size,
                "value": order.executed.price * self.position.size,
                "commission": order.executed.comm
            })
        elif order.issell():
            last_buy_price = self.get_last_buy_price()
            profit = (order.executed.price - last_buy_price) * self.qty_sell_track if last_buy_price else 0
            profit_pct = ((order.executed.price - last_buy_price) / last_buy_price * 100) if last_buy_price else 0
            
            # Update performance metrics
            if profit > 0:
                self.winning_trades += 1
                self.total_profit += profit
            else:
                self.losing_trades += 1
                self.total_loss += abs(profit)
            
            self.trade_journal.append({
                "date": dt,
                "type": "sell",
                "price": order.executed.price,
                "size": self.qty_sell_track,
                "value": order.executed.price * self.qty_sell_track,
                "commission": order.executed.comm,
                "profit": profit,
                "profit_pct": profit_pct
            })
    
    def get_last_buy_date(self) -> Optional[Any]:
        """Get the date of the last buy order"""
        for trade in reversed(self.trade_journal):
            if trade['type'] == 'buy':
                return trade['date']
        return None
    
    def get_last_buy_price(self) -> Optional[float]:
        """Get the price of the last buy order"""
        for trade in reversed(self.trade_journal):
            if trade['type'] == 'buy':
                return trade['price']
        return None
    
    def notify_order(self, order: bt.Order):
        """Handle order notifications"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Size: {self.position.size}, '
                        f'Cost: {order.executed.price * self.position.size:.2f}, '
                        f'Comm: {order.executed.comm:.2f}')
                
                self.buy_price = order.executed.price
                self.buy_size = self.position.size
                self.log_buy = order.executed.price * self.position.size
                self.add_to_journal(order)
                
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Size: {self.qty_sell_track}, '
                        f'Cost: {order.executed.price * self.qty_sell_track:.2f}, '
                        f'Comm: {order.executed.comm:.2f}')
                
                self.add_to_journal(order)
                last_buy_date = self.get_last_buy_date()
                
                # Calculate holding days
                dt = self.datas[0].datetime.date(0)
                if last_buy_date:
                    days_held = (dt - last_buy_date).days
                    self.days_traded += days_held
                    self.log(f'Position held for {days_held} days')
                
                self.log_sell = order.executed.price * self.qty_sell_track
                profit = self.log_sell - self.log_buy
                profit_pct = (profit / self.log_buy) * 100 if self.log_buy > 0 else 0
                
                if profit > 0:
                    self.log(f'TRADE PROFIT: ₹{profit:.2f} ({profit_pct:.2f}%)')
                else:
                    self.log(f'TRADE LOSS: ₹{profit:.2f} ({profit_pct:.2f}%)')
                
                self.log_sell = 0
                self.buy_price = None
                self.buy_size = None
                
            self.bar_executed = len(self)
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        
        self.order = None
    
    def notify_trade(self, trade: bt.Trade):
        """Handle trade notifications"""
        if not trade.isclosed:
            return
        
        self.log(f'TRADE PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}')
    
    def calculate_position_size(self, price: float, percentage: float = 1.0) -> int:
        """
        Calculate position size based on available cash
        
        Args:
            price: Target price for the order
            percentage: Percentage of available cash to use (default 100%)
        
        Returns:
            Number of shares to buy
        """
        available_funds = self.broker.get_cash() * percentage
        qty = math.floor(available_funds / price)
        return max(0, qty)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate and return performance metrics"""
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = (self.total_profit / self.winning_trades) if self.winning_trades > 0 else 0
        avg_loss = (self.total_loss / self.losing_trades) if self.losing_trades > 0 else 0
        
        profit_factor = (self.total_profit / self.total_loss) if self.total_loss > 0 else self.total_profit
        
        return {
            'total_trades': total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'times_in_market': self.times_traded,
            'days_traded': self.days_traded
        }
    
    def stop(self):
        """Called when the strategy stops"""
        metrics = self.get_performance_metrics()
        
        # Calculate annualized return
        start_value = self.broker.startingcash
        end_value = self.broker.getvalue()
        total_return = end_value - start_value
        total_return_pct = (total_return / start_value) * 100 if start_value > 0 else 0
        
        # Annualized return (only if we have meaningful data)
        if metrics["days_traded"] >= 30:  # At least 30 days
            annualized_return = ((end_value / start_value) ** (365 / metrics["days_traded"])) - 1
            annualized_return_pct = annualized_return * 100
        else:
            annualized_return_pct = None
        
        self.log('=' * 50, do_print=True)
        self.log(f'Strategy: {self.__class__.__name__}', do_print=True)
        self.log(f'Total Return: ₹{total_return:.2f} ({total_return_pct:.2f}%)', do_print=True)
        if annualized_return_pct is not None:
            self.log(f'Annualized Return: {annualized_return_pct:.2f}%', do_print=True)
        else:
            self.log(f'Annualized Return: N/A (insufficient days: {metrics["days_traded"]})', do_print=True)
        self.log(f'Total Trades: {metrics["total_trades"]}', do_print=True)
        self.log(f'Winning Trades: {metrics["winning_trades"]}', do_print=True)
        self.log(f'Losing Trades: {metrics["losing_trades"]}', do_print=True)
        self.log(f'Win Rate: {metrics["win_rate"]:.2f}%', do_print=True)
        self.log(f'Profit Factor: {metrics["profit_factor"]:.2f}', do_print=True)
        self.log(f'Days in Market: {metrics["days_traded"]}', do_print=True)
        self.log('=' * 50, do_print=True)
    
    # Abstract methods to be implemented by child classes
    def buy_signal(self) -> bool:
        """Define buy conditions - to be overridden by child classes"""
        raise NotImplementedError("Subclass must implement buy_signal()")
    
    def sell_signal(self) -> bool:
        """Define sell conditions - to be overridden by child classes"""
        raise NotImplementedError("Subclass must implement sell_signal()")
    
    def next(self):
        """Main strategy logic - can be overridden but provides default behavior"""
        # Check if an order is pending
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Check buy signal
            if self.buy_signal():
                self.execute_buy()
        else:
            # Check sell signal
            if self.sell_signal():
                self.execute_sell()
    
    def execute_buy(self):
        """Execute buy order - can be overridden for custom buy logic"""
        self.log(f'BUY CREATE, Close: {self.dataclose[0]:.2f}')
        self.order = self.buy()
    
    def execute_sell(self):
        """Execute sell order - can be overridden for custom sell logic"""
        self.log(f'SELL CREATE, Close: {self.dataclose[0]:.2f}')
        qty_to_sell = self.position.size
        if qty_to_sell > 0:
            self.qty_sell_track = qty_to_sell
            self.order = self.sell(size=qty_to_sell)
            self.times_traded += 1
