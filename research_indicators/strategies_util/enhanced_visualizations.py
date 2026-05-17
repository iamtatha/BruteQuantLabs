"""
Enhanced Visualization Module
==============================

Provides beautiful, informative charts for backtesting analysis:
1. Trade-focused price chart with zoomed regions
2. Equity curve showing portfolio growth
3. Performance metrics dashboard
4. Trade distribution analysis
5. Monthly/yearly returns heatmap
"""

import sys
from pathlib import Path

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import seaborn as sns
from typing import List, Dict, Any, Optional
from matplotlib.backends.backend_pdf import PdfPages

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class StrategyVisualizer:
    """
    Create enhanced visualizations for backtesting results
    """
    
    def __init__(self, df: pd.DataFrame, results: Dict[str, Any], strategy_name: str = "Strategy"):
        """
        Initialize visualizer
        
        Args:
            df: OHLC DataFrame with DatetimeIndex
            results: Results dictionary from backtest
            strategy_name: Name of the strategy
        """
        self.df = df
        self.results = results
        self.strategy_name = strategy_name
        self.trade_journal = results.get('trade_journal', [])
        
    def plot_all(self, figsize=(20, 12), save_path: Optional[str] = None, show: bool = False):
        """
        Create a comprehensive dashboard with all visualizations
        
        Args:
            figsize: Figure size (width, height)
            save_path: Path to save as PDF (if None, defaults to strategy_name.pdf)
            show: Whether to display the plot (default: False, just save)
        """
        # Default PDF filename
        if save_path is None:
            save_path = f"{self.strategy_name.replace(' ', '_')}_dashboard.pdf"
        
        # Ensure .pdf extension
        if not save_path.endswith('.pdf'):
            save_path = save_path.replace('.png', '.pdf')  # Replace if .png was given
            if not save_path.endswith('.pdf'):
                save_path += '.pdf'
        
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # Main price chart with trades (top, spanning 2 columns)
        ax1 = fig.add_subplot(gs[0, :2])
        self._plot_price_with_trades(ax1)
        
        # Equity curve (top right)
        ax2 = fig.add_subplot(gs[0, 2])
        self._plot_equity_curve(ax2)
        
        # Trade zoom regions (middle, spanning all columns)
        ax3 = fig.add_subplot(gs[1, :])
        self._plot_trade_zoom(ax3)
        
        # Performance metrics (bottom left)
        ax4 = fig.add_subplot(gs[2, 0])
        self._plot_metrics_table(ax4)
        
        # Trade distribution (bottom middle)
        ax5 = fig.add_subplot(gs[2, 1])
        self._plot_trade_distribution(ax5)
        
        # Monthly returns heatmap (bottom right)
        ax6 = fig.add_subplot(gs[2, 2])
        self._plot_returns_heatmap(ax6)
        
        plt.suptitle(f'{self.strategy_name} - Performance Analysis', 
                    fontsize=16, fontweight='bold', y=0.995)
        
        # Save to PDF
        plt.savefig(save_path, dpi=300, bbox_inches='tight', format='pdf')
        print(f"Dashboard saved to {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def _plot_price_with_trades(self, ax):
        """Plot price chart with buy/sell markers"""
        # Plot closing price
        ax.plot(self.df.index, self.df['close'], 
               label='close Price', color='blue', alpha=0.6, linewidth=1)
        
        # Extract buy and sell trades
        buys = [t for t in self.trade_journal if t['type'] == 'buy']
        sells = [t for t in self.trade_journal if t['type'] == 'sell']
        
        # Plot buy signals
        if buys:
            buy_dates = [t['date'] for t in buys]
            buy_prices = [t['price'] for t in buys]
            ax.scatter(buy_dates, buy_prices, 
                      marker='^', color='green', s=200, 
                      label='Buy', zorder=5, edgecolors='black', linewidth=1.5)
        
        # Plot sell signals
        if sells:
            sell_dates = [t['date'] for t in sells]
            sell_prices = [t['price'] for t in sells]
            ax.scatter(sell_dates, sell_prices, 
                      marker='v', color='red', s=200, 
                      label='Sell', zorder=5, edgecolors='black', linewidth=1.5)
        
        ax.set_title('Price Chart with Trade Signals', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price (₹)')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def _plot_equity_curve(self, ax):
        """Plot equity curve showing portfolio growth"""
        # Build equity curve from trade journal
        equity_curve = self._build_equity_curve()
        
        if equity_curve:
            dates, values = zip(*equity_curve)
            ax.plot(dates, values, color='darkgreen', linewidth=2.5)
            ax.fill_between(dates, values, 
                           alpha=0.3, color='green')
            
            # Mark max drawdown
            if len(values) > 1:
                peak = np.maximum.accumulate(values)
                drawdown = (np.array(values) - peak) / peak * 100
                max_dd_idx = np.argmin(drawdown)
                
                ax.plot(dates[max_dd_idx], values[max_dd_idx], 
                       'ro', markersize=8, label=f'Max DD: {drawdown[max_dd_idx]:.1f}%')
        
        ax.set_title('Equity Curve', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value (₹)')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def _plot_trade_zoom(self, ax):
        """Plot zoomed regions around trades for detailed view"""
        if not self.trade_journal:
            ax.text(0.5, 0.5, 'No trades to display', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Trade Details (No trades executed)', fontweight='bold')
            return
        
        # Group trades into pairs (buy-sell)
        trade_pairs = []
        buys = [t for t in self.trade_journal if t['type'] == 'buy']
        sells = [t for t in self.trade_journal if t['type'] == 'sell']
        
        for i, buy in enumerate(buys):
            if i < len(sells):
                trade_pairs.append((buy, sells[i]))
        
        if not trade_pairs:
            ax.text(0.5, 0.5, 'No complete trade pairs', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Trade Details', fontweight='bold')
            return
        
        # Plot each trade with surrounding context
        for i, (buy, sell) in enumerate(trade_pairs[:5]):  # Show max 5 trades
            # Get data around trade
            buy_date = buy['date']
            sell_date = sell['date']
            
            # Convert to pandas Timestamp if needed
            if not isinstance(buy_date, pd.Timestamp):
                buy_date = pd.Timestamp(buy_date)
            if not isinstance(sell_date, pd.Timestamp):
                sell_date = pd.Timestamp(sell_date)
            
            # Window: 10 days before buy to 10 days after sell
            start_date = buy_date - timedelta(days=10)
            end_date = sell_date + timedelta(days=10)
            
            mask = (self.df.index >= start_date) & (self.df.index <= end_date)
            trade_df = self.df[mask]
            
            if len(trade_df) > 0:
                # Offset for multiple trades
                offset = i * (max(trade_df['close']) - min(trade_df['close'])) * 1.2
                
                # Plot price line
                ax.plot(trade_df.index, trade_df['close'] + offset, 
                       alpha=0.7, linewidth=1.5, label=f'Trade {i+1}')
                
                # Mark buy
                ax.scatter([buy_date], [buy['price'] + offset], 
                          marker='^', color='green', s=150, zorder=5, 
                          edgecolors='black', linewidth=1)
                
                # Mark sell
                ax.scatter([sell_date], [sell['price'] + offset], 
                          marker='v', color='red', s=150, zorder=5,
                          edgecolors='black', linewidth=1)
                
                # Add profit annotation
                profit_pct = sell.get('profit_pct', 0)
                mid_date = buy_date + (sell_date - buy_date) / 2
                mid_price = (buy['price'] + sell['price']) / 2 + offset
                
                color = 'green' if profit_pct > 0 else 'red'
                ax.annotate(f'{profit_pct:+.1f}%', 
                           xy=(mid_date, mid_price),
                           fontsize=9, fontweight='bold', color=color,
                           ha='center', 
                           bbox=dict(boxstyle='round,pad=0.3', 
                                   facecolor='white', alpha=0.7))
        
        ax.set_title('Trade Details (Zoomed View)', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price (₹) - Offset per trade')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def _plot_metrics_table(self, ax):
        """Display performance metrics as a table"""
        ax.axis('off')
        
        def fmt(value, decimals=2, prefix='', suffix=''):
            if value is None or (isinstance(value, float) and not np.isfinite(value)):
                return 'N/A'
            return f"{prefix}{value:.{decimals}f}{suffix}"
        
        metrics = [
            ['Metric', 'Value'],
            ['Total Return', fmt(self.results.get('total_return_pct', 0), suffix='%')],
            ['Annualized Return', fmt(self.results.get('annualized_return_pct', 0), suffix='%')],
            ['Sharpe Ratio', fmt(self.results.get('sharpe_ratio'))],
            ['Max Drawdown', fmt(self.results.get('max_drawdown_pct', 0), suffix='%')],
            ['Win Rate', fmt(self.results.get('win_rate', 0), suffix='%')],
            ['Profit Factor', fmt(self.results.get('profit_factor', 0))],
            ['Total Trades', str(self.results.get('total_trades', 0))],
            ['Avg Win', fmt(self.results.get('avg_win', 0), prefix='₹')],
            ['Avg Loss', fmt(self.results.get('avg_loss', 0), prefix='₹')],
    ]
        
        table = ax.table(cellText=metrics, 
                        cellLoc='left',
                        loc='center',
                        colWidths=[0.6, 0.4])
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # Style header row
        for i in range(2):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Alternate row colors
        for i in range(1, len(metrics)):
            for j in range(2):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#f0f0f0')
        
        ax.set_title('Performance Metrics', fontweight='bold', pad=20)
    
    def _plot_trade_distribution(self, ax):
        """Plot distribution of trade returns"""
        if not self.trade_journal:
            ax.text(0.5, 0.5, 'No trades to analyze', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Trade Distribution', fontweight='bold')
            return
        
        # Extract profit percentages
        profits = [t.get('profit_pct', 0) for t in self.trade_journal 
                  if t['type'] == 'sell']
        
        if profits:
            # Create histogram
            colors = ['green' if p > 0 else 'red' for p in profits]
            ax.bar(range(len(profits)), profits, color=colors, alpha=0.7, 
                  edgecolor='black', linewidth=1)
            
            # Add zero line
            ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
            
            # Add average line
            avg_profit = np.mean(profits)
            ax.axhline(y=avg_profit, color='blue', linestyle='--', 
                      linewidth=2, label=f'Avg: {avg_profit:.2f}%')
            
            ax.set_title('Trade Returns Distribution', fontweight='bold')
            ax.set_xlabel('Trade Number')
            ax.set_ylabel('Return (%)')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
        else:
            ax.text(0.5, 0.5, 'No completed trades', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_returns_heatmap(self, ax):
        """Plot monthly returns heatmap"""
        equity_curve = self._build_equity_curve()
        
        if not equity_curve or len(equity_curve) < 2:
            ax.text(0.5, 0.5, 'Insufficient data\nfor heatmap', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Monthly Returns', fontweight='bold')
            ax.axis('off')
            return
        
        # Convert to DataFrame
        df_equity = pd.DataFrame(equity_curve, columns=['date', 'value'])
        df_equity['date'] = pd.to_datetime(df_equity['date'])
        df_equity.set_index('date', inplace=True)
        
        # Calculate monthly returns
        df_equity['returns'] = df_equity['value'].pct_change() * 100
        df_equity['year'] = df_equity.index.year
        df_equity['month'] = df_equity.index.month
        
        # Pivot for heatmap
        monthly_returns = df_equity.groupby(['year', 'month'])['returns'].sum().unstack(fill_value=0)
        
        if monthly_returns.empty:
            ax.text(0.5, 0.5, 'No monthly data', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            return
        
        # Create heatmap
        sns.heatmap(monthly_returns, annot=True, fmt='.1f', 
                   cmap='RdYlGn', center=0, ax=ax, 
                   cbar_kws={'label': 'Return (%)'},
                   linewidths=0.5)
        
        ax.set_title('Monthly Returns (%)', fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('Year')
    
    def _build_equity_curve(self) -> List[tuple]:
        """Build equity curve from trade journal"""
        if not self.trade_journal:
            return []
        
        start_value = self.results.get('start_value', 100000)
        equity = start_value
        
        # Convert first date to Timestamp
        first_date = self.trade_journal[0]['date']
        if not isinstance(first_date, pd.Timestamp):
            first_date = pd.Timestamp(first_date)
        
        equity_curve = [(first_date, start_value)]
        
        for trade in self.trade_journal:
            if trade['type'] == 'sell':
                profit = trade.get('profit', 0)
                equity += profit
                
                # Convert date to Timestamp
                trade_date = trade['date']
                if not isinstance(trade_date, pd.Timestamp):
                    trade_date = pd.Timestamp(trade_date)
                
                equity_curve.append((trade_date, equity))
        
        # Add final value
        end_value = self.results.get('end_value', equity)
        if equity_curve:
            last_date = self.trade_journal[-1]['date']
            if not isinstance(last_date, pd.Timestamp):
                last_date = pd.Timestamp(last_date)
            equity_curve.append((last_date, end_value))
        
        return equity_curve
    
    def plot_equity_curve_detailed(self, figsize=(14, 6), save_path: Optional[str] = None, show: bool = False):
        """
        Create a detailed standalone equity curve plot
        
        Args:
            figsize: Figure size
            save_path: Path to save as PDF (if None, defaults to strategy_name_equity.pdf)
            show: Whether to display the plot (default: False, just save)
        """
        # Default PDF filename
        if save_path is None:
            save_path = f"{self.strategy_name.replace(' ', '_')}_equity.pdf"
        
        # Ensure .pdf extension
        if not save_path.endswith('.pdf'):
            save_path = save_path.replace('.png', '.pdf')
            if not save_path.endswith('.pdf'):
                save_path += '.pdf'
        
        equity_curve = self._build_equity_curve()
        
        if not equity_curve:
            print("No equity data to plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, 
                                       gridspec_kw={'height_ratios': [2, 1]})
        
        dates, values = zip(*equity_curve)
        values = np.array(values)
        
        # Plot equity curve
        ax1.plot(dates, values, color='darkblue', linewidth=2.5, label='Portfolio Value')
        ax1.fill_between(dates, values, alpha=0.3, color='blue')
        
        # Calculate and plot peak
        peak = np.maximum.accumulate(values)
        ax1.plot(dates, peak, '--', color='green', alpha=0.5, linewidth=1.5, label='Peak Value')
        
        # Highlight drawdown periods
        drawdown = values - peak
        ax1.fill_between(dates, peak, values, where=(drawdown < 0), 
                        color='red', alpha=0.2, label='Drawdown')
        
        ax1.set_title(f'{self.strategy_name} - Equity Curve', fontweight='bold', fontsize=14)
        ax1.set_ylabel('Portfolio Value (₹)', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
        
        # Plot drawdown percentage
        drawdown_pct = (drawdown / peak) * 100
        ax2.fill_between(dates, 0, drawdown_pct, color='red', alpha=0.5)
        ax2.plot(dates, drawdown_pct, color='darkred', linewidth=1.5)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
        
        ax2.set_title('Drawdown %', fontweight='bold', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Rotate x-axis labels
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save to PDF
        plt.savefig(save_path, dpi=300, bbox_inches='tight', format='pdf')
        print(f"Equity curve saved to {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_trade_analysis(self, figsize=(16, 10), save_path: Optional[str] = None, show: bool = False):
        """
        Create detailed trade-by-trade analysis charts
        
        Args:
            figsize: Figure size
            save_path: Path to save as PDF (if None, defaults to strategy_name_trades.pdf)
            show: Whether to display the plot (default: False, just save)
        """
        if not self.trade_journal:
            print("No trades to analyze")
            return
        
        # Default PDF filename
        if save_path is None:
            save_path = f"{self.strategy_name.replace(' ', '_')}_trades.pdf"
        
        # Ensure .pdf extension
        if not save_path.endswith('.pdf'):
            save_path = save_path.replace('.png', '.pdf')
            if not save_path.endswith('.pdf'):
                save_path += '.pdf'
        
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)
        
        # 1. Cumulative profit chart
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_cumulative_profit(ax1)
        
        # 2. Win/Loss streak
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_win_loss_streak(ax2)
        
        # 3. Profit by holding period
        ax3 = fig.add_subplot(gs[1, 0])
        self._plot_profit_by_holding_period(ax3)
        
        # 4. Entry/Exit time analysis
        ax4 = fig.add_subplot(gs[1, 1])
        self._plot_time_analysis(ax4)
        
        plt.suptitle(f'{self.strategy_name} - Trade Analysis', 
                    fontsize=16, fontweight='bold')
        
        # Save to PDF
        plt.savefig(save_path, dpi=300, bbox_inches='tight', format='pdf')
        print(f"Trade analysis saved to {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def create_full_report_pdf(self, save_path: Optional[str] = None):
        """
        Create a single comprehensive PDF report with all visualizations
        
        Args:
            save_path: Path to save the PDF (if None, defaults to strategy_name_report.pdf)
        
        Returns:
            Path to the saved PDF file
        """
        # Default PDF filename
        if save_path is None:
            save_path = f"research_indicators/strategy_reports/{self.strategy_name.replace(' ', '_')}_full_report.pdf"
        
        # Ensure .pdf extension
        if not save_path.endswith('.pdf'):
            save_path = save_path.replace('.png', '.pdf')
            if not save_path.endswith('.pdf'):
                save_path += '.pdf'
        
        print(f"Generating comprehensive PDF report: {save_path}")
        
        # Create PDF
        with PdfPages(save_path) as pdf:
            
            # Page 1: Dashboard
            print("  [1/3] Creating dashboard page...")
            fig1 = plt.figure(figsize=(20, 12))
            gs1 = GridSpec(3, 3, figure=fig1, hspace=0.3, wspace=0.3)
            
            ax1 = fig1.add_subplot(gs1[0, :2])
            self._plot_price_with_trades(ax1)
            
            ax2 = fig1.add_subplot(gs1[0, 2])
            self._plot_equity_curve(ax2)
            
            ax3 = fig1.add_subplot(gs1[1, :])
            self._plot_trade_zoom(ax3)
            
            ax4 = fig1.add_subplot(gs1[2, 0])
            self._plot_metrics_table(ax4)
            
            ax5 = fig1.add_subplot(gs1[2, 1])
            self._plot_trade_distribution(ax5)
            
            ax6 = fig1.add_subplot(gs1[2, 2])
            self._plot_returns_heatmap(ax6)
            
            plt.suptitle(f'{self.strategy_name} - Performance Dashboard', 
                        fontsize=16, fontweight='bold', y=0.995)
            
            pdf.savefig(fig1, bbox_inches='tight')
            plt.close(fig1)
            
            # Page 2: Detailed Equity Curve
            print("  [2/3] Creating equity curve page...")
            equity_curve = self._build_equity_curve()
            
            if equity_curve:
                fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                               gridspec_kw={'height_ratios': [2, 1]})
                
                dates, values = zip(*equity_curve)
                values = np.array(values)
                
                # Plot equity curve
                ax1.plot(dates, values, color='darkblue', linewidth=2.5, label='Portfolio Value')
                ax1.fill_between(dates, values, alpha=0.3, color='blue')
                
                # Calculate and plot peak
                peak = np.maximum.accumulate(values)
                ax1.plot(dates, peak, '--', color='green', alpha=0.5, linewidth=1.5, label='Peak Value')
                
                # Highlight drawdown periods
                drawdown = values - peak
                ax1.fill_between(dates, peak, values, where=(drawdown < 0), 
                                color='red', alpha=0.2, label='Drawdown')
                
                ax1.set_title(f'{self.strategy_name} - Equity Curve', fontweight='bold', fontsize=14)
                ax1.set_ylabel('Portfolio Value (₹)', fontsize=12)
                ax1.legend(loc='best')
                ax1.grid(True, alpha=0.3)
                ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
                
                # Plot drawdown percentage
                drawdown_pct = (drawdown / peak) * 100
                ax2.fill_between(dates, 0, drawdown_pct, color='red', alpha=0.5)
                ax2.plot(dates, drawdown_pct, color='darkred', linewidth=1.5)
                ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
                
                ax2.set_title('Drawdown %', fontweight='bold', fontsize=12)
                ax2.set_xlabel('Date', fontsize=12)
                ax2.set_ylabel('Drawdown (%)', fontsize=12)
                ax2.grid(True, alpha=0.3)
                
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
                plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
                
                plt.tight_layout()
                
                pdf.savefig(fig2, bbox_inches='tight')
                plt.close(fig2)
            
            # Page 3: Trade Analysis
            if self.trade_journal:
                print("  [3/3] Creating trade analysis page...")
                fig3 = plt.figure(figsize=(16, 10))
                gs3 = GridSpec(2, 2, figure=fig3, hspace=0.3, wspace=0.3)
                
                ax1 = fig3.add_subplot(gs3[0, 0])
                self._plot_cumulative_profit(ax1)
                
                ax2 = fig3.add_subplot(gs3[0, 1])
                self._plot_win_loss_streak(ax2)
                
                ax3 = fig3.add_subplot(gs3[1, 0])
                self._plot_profit_by_holding_period(ax3)
                
                ax4 = fig3.add_subplot(gs3[1, 1])
                self._plot_time_analysis(ax4)
                
                plt.suptitle(f'{self.strategy_name} - Trade Analysis', 
                            fontsize=16, fontweight='bold')
                
                pdf.savefig(fig3, bbox_inches='tight')
                plt.close(fig3)
            
            # Set PDF metadata
            d = pdf.infodict()
            d['Title'] = f'{self.strategy_name} - Backtest Report'
            d['Author'] = 'Trading Strategy Backtesting Framework'
            d['Subject'] = 'Strategy Performance Analysis'
            d['Keywords'] = f'Backtest, {self.strategy_name}, Trading Strategy'
            d['CreationDate'] = datetime.now()
        
        print(f"✓ Complete PDF report saved to {save_path}")
        return save_path

    def _plot_cumulative_profit(self, ax):
        """Plot cumulative profit over time"""
        sells = [t for t in self.trade_journal if t['type'] == 'sell']
        
        if not sells:
            ax.text(0.5, 0.5, 'No sell trades', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        cumulative_profit = np.cumsum([t.get('profit', 0) for t in sells])
        trade_numbers = range(1, len(cumulative_profit) + 1)
        
        colors = ['green' if p > 0 else 'red' for p in cumulative_profit]
        ax.plot(trade_numbers, cumulative_profit, marker='o', linewidth=2, markersize=8)
        
        for i, (x, y, c) in enumerate(zip(trade_numbers, cumulative_profit, colors)):
            ax.plot(x, y, 'o', color=c, markersize=10)
        
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.set_title('Cumulative Profit', fontweight='bold')
        ax.set_xlabel('Trade Number')
        ax.set_ylabel('Cumulative Profit (₹)')
        ax.grid(True, alpha=0.3)
    
    def _plot_win_loss_streak(self, ax):
        """Plot win/loss streaks"""
        sells = [t for t in self.trade_journal if t['type'] == 'sell']
        
        if not sells:
            ax.text(0.5, 0.5, 'No sell trades', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        outcomes = [1 if t.get('profit', 0) > 0 else -1 for t in sells]
        
        colors = ['green' if o > 0 else 'red' for o in outcomes]
        ax.bar(range(1, len(outcomes) + 1), outcomes, color=colors, alpha=0.7, edgecolor='black')
        
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1.5)
        ax.set_title('Win/Loss Pattern', fontweight='bold')
        ax.set_xlabel('Trade Number')
        ax.set_ylabel('Win (+1) / Loss (-1)')
        ax.set_ylim([-1.5, 1.5])
        ax.grid(True, alpha=0.3, axis='x')
    
    def _plot_profit_by_holding_period(self, ax):
        """Plot profit vs holding period"""
        buys = {t['date']: t for t in self.trade_journal if t['type'] == 'buy'}
        sells = [t for t in self.trade_journal if t['type'] == 'sell']
        
        if not sells:
            ax.text(0.5, 0.5, 'No sell trades', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        holding_periods = []
        profits = []
        
        for sell in sells:
            # Find matching buy
            buy_date = None
            for date in sorted(buys.keys(), reverse=True):
                if date <= sell['date']:
                    buy_date = date
                    break
            
            if buy_date:
                holding_days = (sell['date'] - buy_date).days
                holding_periods.append(holding_days)
                profits.append(sell.get('profit_pct', 0))
        
        if holding_periods:
            colors = ['green' if p > 0 else 'red' for p in profits]
            ax.scatter(holding_periods, profits, c=colors, s=100, alpha=0.6, edgecolors='black')
            
            ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
            ax.set_title('Profit vs Holding Period', fontweight='bold')
            ax.set_xlabel('Holding Period (days)')
            ax.set_ylabel('Profit (%)')
            ax.grid(True, alpha=0.3)
    
    def _plot_time_analysis(self, ax):
        """Analyze trade entry times"""
        sells = [t for t in self.trade_journal if t['type'] == 'sell']
        
        if not sells:
            ax.text(0.5, 0.5, 'No sell trades', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        # Group by month
        monthly_profits = {}
        for sell in sells:
            month = sell['date'].strftime('%Y-%m')
            profit = sell.get('profit', 0)
            monthly_profits[month] = monthly_profits.get(month, 0) + profit
        
        if monthly_profits:
            months = list(monthly_profits.keys())
            profits = list(monthly_profits.values())
            colors = ['green' if p > 0 else 'red' for p in profits]
            
            ax.bar(range(len(months)), profits, color=colors, alpha=0.7, edgecolor='black')
            ax.set_xticks(range(len(months)))
            ax.set_xticklabels(months, rotation=45, ha='right')
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
            
            ax.set_title('Monthly Profit Distribution', fontweight='bold')
            ax.set_xlabel('Month')
            ax.set_ylabel('Total Profit (₹)')
            ax.grid(True, alpha=0.3, axis='y')


# Convenience function
def visualize_backtest_results(df: pd.DataFrame, 
                               results: Dict[str, Any],
                               strategy_name: str = "Strategy",
                               show_all: bool = False,
                               show_equity: bool = False,
                               show_trades: bool = False,
                               save_pdf: bool = True,
                               base_path: str =None,
                               save_prefix: Optional[str] = None):
    """
    Convenience function to generate all visualizations as PDF
    
    Args:
        df: OHLC DataFrame
        results: Results dictionary from backtest
        strategy_name: Name of the strategy
        show_all: Show comprehensive dashboard (displays window, not recommended)
        show_equity: Show detailed equity curve (displays window, not recommended)
        show_trades: Show trade analysis (displays window, not recommended)
        save_pdf: Save as PDF report (default: True, recommended)
        save_prefix: Prefix for saved files (optional)
    
    Note:
        By default, this creates a single comprehensive PDF with all visualizations.
        Set save_pdf=False and show_* flags to True if you want to display windows instead.
    
    Example:
        >>> from enhanced_visualizations import visualize_backtest_results
        >>> visualize_backtest_results(df, results, "Bollinger Band", 
        ...                            save_pdf=True,
        ...                            save_prefix="TCS_bollinger")
        # Creates: TCS_bollinger_full_report.pdf
    """
        
    viz = StrategyVisualizer(df, results, strategy_name)
    
    # ONLY creates one comprehensive PDF
    if base_path is None:
        base_path = "research_indicators/strategy_reports"
    
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        
    if save_prefix:
        pdf_path = f"{base_path}/{save_prefix}.pdf"
    else:
        pdf_path = None
    
    return viz.create_full_report_pdf(save_path=pdf_path)




