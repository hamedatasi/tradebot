"""
Comprehensive backtesting engine for trading strategies.
Supports historical data replay, performance metrics, and strategy optimization.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json


@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: int
    exit_time: Optional[int]
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    max_drawdown: float = 0.0
    max_profit: float = 0.0
    exit_reason: str = ""  # STOP_LOSS, TAKE_PROFIT, SIGNAL, etc.


@dataclass
class BacktestResult:
    """Backtesting performance results."""
    total_return: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_duration: float = 0.0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'total_return': self.total_return,
            'total_return_pct': self.total_return_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'trades': [
                {
                    'entry_time': t.entry_time,
                    'exit_time': t.exit_time,
                    'symbol': t.symbol,
                    'side': t.side,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct
                }
                for t in self.trades
            ]
        }


class BacktestEngine:
    """
    Comprehensive backtesting engine with realistic simulation.
    """
    
    def __init__(self, initial_capital: float = 10000.0, 
                 commission_rate: float = 0.001,
                 slippage_rate: float = 0.0005):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        self.capital = initial_capital
        self.position = 0  # Current position size
        self.position_value = 0.0
        self.open_trades: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
    
    def reset(self):
        """Reset backtest state."""
        self.capital = self.initial_capital
        self.position = 0
        self.position_value = 0.0
        self.open_trades = {}
        self.closed_trades = []
        self.equity_curve = []
        self.peak_equity = self.initial_capital
        self.max_drawdown = 0.0
    
    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to execution price."""
        slippage = price * self.slippage_rate
        if side == 'BUY':
            return price + slippage
        else:
            return price - slippage
    
    def _calculate_commission(self, value: float) -> float:
        """Calculate trading commission."""
        return value * self.commission_rate
    
    def run(self, candles: List[Dict], signals: List, 
            stop_loss_pct: float = 2.0, take_profit_pct: float = 5.0,
            position_size_pct: float = 0.1) -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            candles: List of OHLCV candles
            signals: List of signals aligned with candles
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            position_size_pct: Position size as % of capital
        """
        self.reset()
        
        if not candles or not signals:
            return BacktestResult()
        
        # Ensure signals align with candles
        signal_map = {s.timestamp: s for s in signals}
        
        for i, candle in enumerate(candles):
            timestamp = candle['timestamp']
            current_price = candle['close']
            
            # Update equity curve
            current_equity = self.capital + self.position * current_price
            self.equity_curve.append(current_equity)
            
            # Track peak and drawdown
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
            
            drawdown = (self.peak_equity - current_equity) / self.peak_equity
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            
            # Check existing positions for stop loss / take profit
            self._check_exits(candle, stop_loss_pct, take_profit_pct)
            
            # Process signals
            if timestamp in signal_map:
                signal = signal_map[timestamp]
                
                if signal.action == 'BUY' and self.position <= 0:
                    self._open_position(
                        symbol=signal.symbol,
                        side='LONG',
                        price=current_price,
                        quantity=(self.capital * position_size_pct) / current_price,
                        timestamp=timestamp
                    )
                
                elif signal.action == 'SELL' and self.position >= 0:
                    self._open_position(
                        symbol=signal.symbol,
                        side='SHORT',
                        price=current_price,
                        quantity=(self.capital * position_size_pct) / current_price,
                        timestamp=timestamp
                    )
        
        # Close any remaining open positions at last price
        self._close_all_positions(candles[-1], "END_OF_BACKTEST")
        
        return self._generate_result()
    
    def _open_position(self, symbol: str, side: str, price: float, 
                      quantity: float, timestamp: int):
        """Open a new position."""
        exec_price = self._apply_slippage(price, 'BUY' if side == 'LONG' else 'SELL')
        position_value = exec_price * quantity
        commission = self._calculate_commission(position_value)
        
        if self.capital < position_value + commission:
            # Not enough capital
            return
        
        self.capital -= commission
        
        trade = Trade(
            entry_time=timestamp,
            exit_time=None,
            symbol=symbol,
            side=side,
            entry_price=exec_price,
            exit_price=None,
            quantity=quantity,
            commission=commission
        )
        
        self.open_trades[symbol] = trade
        self.position = quantity if side == 'LONG' else -quantity
        self.position_value = position_value
    
    def _close_position(self, symbol: str, candle: Dict, reason: str):
        """Close an existing position."""
        if symbol not in self.open_trades:
            return
        
        trade = self.open_trades[symbol]
        current_price = candle['close']
        side = 'SELL' if trade.side == 'LONG' else 'BUY'
        
        exec_price = self._apply_slippage(current_price, side)
        position_value = exec_price * trade.quantity
        commission = self._calculate_commission(position_value)
        
        # Calculate PnL
        if trade.side == 'LONG':
            pnl = (exec_price - trade.entry_price) * trade.quantity
        else:
            pnl = (trade.entry_price - exec_price) * trade.quantity
        
        pnl -= commission  # Net PnL after commission
        
        # Update trade
        trade.exit_time = candle['timestamp']
        trade.exit_price = exec_price
        trade.pnl = pnl
        trade.pnl_pct = pnl / (trade.entry_price * trade.quantity) * 100
        trade.commission += commission
        trade.exit_reason = reason
        
        # Update capital
        self.capital += pnl + (trade.entry_price * trade.quantity)
        
        # Move to closed trades
        self.closed_trades.append(trade)
        del self.open_trades[symbol]
        
        self.position = 0
        self.position_value = 0
    
    def _check_exits(self, candle: Dict, stop_loss_pct: float, take_profit_pct: float):
        """Check if any positions should be exited."""
        current_price = candle['close']
        
        for symbol in list(self.open_trades.keys()):
            trade = self.open_trades[symbol]
            
            if trade.side == 'LONG':
                # Check stop loss
                if current_price <= trade.entry_price * (1 - stop_loss_pct / 100):
                    self._close_position(symbol, candle, "STOP_LOSS")
                    continue
                
                # Check take profit
                if current_price >= trade.entry_price * (1 + take_profit_pct / 100):
                    self._close_position(symbol, candle, "TAKE_PROFIT")
                    continue
            
            else:  # SHORT
                # Check stop loss
                if current_price >= trade.entry_price * (1 + stop_loss_pct / 100):
                    self._close_position(symbol, candle, "STOP_LOSS")
                    continue
                
                # Check take profit
                if current_price <= trade.entry_price * (1 - take_profit_pct / 100):
                    self._close_position(symbol, candle, "TAKE_PROFIT")
                    continue
    
    def _close_all_positions(self, candle: Dict, reason: str):
        """Close all open positions."""
        for symbol in list(self.open_trades.keys()):
            self._close_position(symbol, candle, reason)
    
    def _generate_result(self) -> BacktestResult:
        """Generate comprehensive backtest results."""
        result = BacktestResult()
        result.trades = self.closed_trades
        result.equity_curve = self.equity_curve
        
        # Basic metrics
        result.total_trades = len(self.closed_trades)
        result.total_return = self.capital - self.initial_capital
        result.total_return_pct = (result.total_return / self.initial_capital) * 100
        result.max_drawdown_pct = self.max_drawdown * 100
        result.max_drawdown = self.peak_equity * self.max_drawdown
        
        # Win/Loss analysis
        winning = [t for t in self.closed_trades if t.pnl > 0]
        losing = [t for t in self.closed_trades if t.pnl <= 0]
        
        result.winning_trades = len(winning)
        result.losing_trades = len(losing)
        
        if result.total_trades > 0:
            result.win_rate = result.winning_trades / result.total_trades * 100
        
        if winning:
            result.avg_win = sum(t.pnl for t in winning) / len(winning)
        
        if losing:
            result.avg_loss = abs(sum(t.pnl for t in losing) / len(losing))
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 1
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe Ratio (assuming daily returns, 252 trading days)
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            if np.std(returns) > 0:
                result.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
            
            # Sortino Ratio (downside deviation)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0 and np.std(downside_returns) > 0:
                result.sortino_ratio = np.mean(returns) / np.std(downside_returns) * np.sqrt(252)
        
        # Average trade duration
        durations = [t.exit_time - t.entry_time for t in self.closed_trades if t.exit_time]
        if durations:
            result.avg_trade_duration = np.mean(durations)
        
        return result
    
    def optimize_parameters(self, candles: List[Dict], signals: List,
                           param_grid: Dict[str, List], metric: str = 'sharpe_ratio') -> Dict:
        """
        Optimize strategy parameters using grid search.
        
        Args:
            candles: Historical candle data
            signals: Signal list
            param_grid: Dictionary of parameter names and values to test
            metric: Metric to optimize ('sharpe_ratio', 'total_return', 'win_rate', etc.)
        
        Returns:
            Best parameters and corresponding results
        """
        from itertools import product
        
        best_result = None
        best_params = None
        best_metric_value = float('-inf')
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            
            # Run backtest with current parameters
            result = self.run(
                candles=candles,
                signals=signals,
                stop_loss_pct=params.get('stop_loss_pct', 2.0),
                take_profit_pct=params.get('take_profit_pct', 5.0),
                position_size_pct=params.get('position_size_pct', 0.1)
            )
            
            # Get metric value
            metric_value = getattr(result, metric, 0)
            
            if metric_value > best_metric_value:
                best_metric_value = metric_value
                best_params = params
                best_result = result
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_metric_value': best_metric_value
        }
    
    def generate_report(self, result: BacktestResult) -> str:
        """Generate human-readable backtest report."""
        report = f"""
=== BACKTEST REPORT ===

Performance Summary:
-------------------
Total Return: ${result.total_return:.2f} ({result.total_return_pct:.2f}%)
Sharpe Ratio: {result.sharpe_ratio:.2f}
Sortino Ratio: {result.sortino_ratio:.2f}
Max Drawdown: ${result.max_drawdown:.2f} ({result.max_drawdown_pct:.2f}%)

Trade Statistics:
----------------
Total Trades: {result.total_trades}
Winning Trades: {result.winning_trades} ({result.win_rate:.1f}%)
Losing Trades: {result.losing_trades}
Profit Factor: {result.profit_factor:.2f}

Average Metrics:
---------------
Avg Win: ${result.avg_win:.2f}
Avg Loss: ${result.avg_loss:.2f}
Win/Loss Ratio: {result.avg_win / result.avg_loss if result.avg_loss > 0 else 'N/A':.2f}
Avg Trade Duration: {result.avg_trade_duration / 3600:.1f} hours

=====================
"""
        return report
    
    def save_results(self, result: BacktestResult, filename: str):
        """Save backtest results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
