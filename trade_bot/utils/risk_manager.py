"""
Risk Management module for position sizing, stop-loss, and portfolio protection.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class PositionSizingMethod(Enum):
    """Position sizing methods."""
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    KELLY = "kelly"
    VOLATILITY = "volatility"
    RISK_PARITY = "risk_parity"


@dataclass
class RiskParameters:
    """Risk management parameters."""
    max_position_size_usd: float = 1000.0
    max_position_pct: float = 0.1  # 10% of portfolio
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 5.0
    max_daily_loss_usd: float = 500.0
    max_daily_loss_pct: float = 5.0
    max_open_positions: int = 5
    leverage: float = 1.0
    risk_per_trade_pct: float = 1.0
    kelly_criterion_max: float = 0.25  # Max 25% even if Kelly suggests more
    correlation_threshold: float = 0.7  # Max correlation between positions


class RiskManager:
    """
    Advanced risk management system for trading operations.
    """
    
    def __init__(self, params: RiskParameters = None):
        self.params = params or RiskParameters()
        self.daily_pnl = 0.0
        self.open_positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.portfolio_value = 0.0
    
    def set_portfolio_value(self, value: float):
        """Set current portfolio value for percentage calculations."""
        self.portfolio_value = value
    
    def calculate_position_size(self, method: PositionSizingMethod,
                               signal_strength: float = 1.0,
                               win_rate: float = 0.5,
                               avg_win_loss_ratio: float = 1.5,
                               volatility: float = None) -> float:
        """
        Calculate position size based on selected method.
        
        Args:
            method: Position sizing method
            signal_strength: Confidence in the signal (0-1)
            win_rate: Historical win rate of strategy
            avg_win_loss_ratio: Average win / average loss ratio
            volatility: Current asset volatility (ATR or std dev)
        
        Returns:
            Position size in USD
        """
        if method == PositionSizingMethod.FIXED:
            return self.params.max_position_size_usd
        
        elif method == PositionSizingMethod.PERCENTAGE:
            base_size = self.portfolio_value * self.params.max_position_pct
            return base_size * signal_strength
        
        elif method == PositionSizingMethod.KELLY:
            # Kelly Criterion: f* = (p*b - q) / b
            # where p = win probability, b = win/loss ratio, q = 1-p
            p = win_rate
            q = 1 - p
            b = avg_win_loss_ratio
            
            if b > 0:
                kelly_fraction = (p * b - q) / b
                kelly_fraction = max(0, min(kelly_fraction, self.params.kelly_criterion_max))
                return self.portfolio_value * kelly_fraction * signal_strength
            else:
                return self.params.max_position_size_usd
        
        elif method == PositionSizingMethod.VOLATILITY:
            # Size inversely proportional to volatility
            if volatility and volatility > 0:
                target_vol = 0.02  # Target 2% daily volatility
                position_value = (self.portfolio_value * target_vol) / volatility
                position_value = min(position_value, self.params.max_position_size_usd)
                return position_value * signal_strength
            else:
                return self.params.max_position_size_usd
        
        elif method == PositionSizingMethod.RISK_PARITY:
            # Equal risk contribution from each position
            if len(self.open_positions) > 0:
                max_positions = self.params.max_open_positions
                risk_per_position = 1.0 / min(len(self.open_positions) + 1, max_positions)
                return self.portfolio_value * risk_per_position * signal_strength
            else:
                return self.portfolio_value * 0.2 * signal_strength
        
        return self.params.max_position_size_usd
    
    def check_risk_limits(self, symbol: str, side: str, 
                         quantity: float, price: float) -> Dict:
        """
        Check if a trade passes all risk limits.
        
        Returns:
            Dictionary with 'approved' boolean and 'reason' if rejected
        """
        position_value = quantity * price
        
        # Check daily loss limit
        if self.daily_pnl < -self.params.max_daily_loss_usd:
            return {
                'approved': False,
                'reason': f'Daily loss limit reached: ${self.daily_pnl:.2f}'
            }
        
        daily_loss_pct = abs(self.daily_pnl) / self.portfolio_value if self.portfolio_value > 0 else 0
        if daily_loss_pct > self.params.max_daily_loss_pct / 100:
            return {
                'approved': False,
                'reason': f'Daily loss percentage limit reached: {daily_loss_pct*100:.2f}%'
            }
        
        # Check max open positions
        if len(self.open_positions) >= self.params.max_open_positions:
            return {
                'approved': False,
                'reason': f'Maximum open positions reached: {len(self.open_positions)}'
            }
        
        # Check position size limit
        if position_value > self.params.max_position_size_usd:
            return {
                'approved': False,
                'reason': f'Position size ${position_value:.2f} exceeds limit ${self.params.max_position_size_usd:.2f}'
            }
        
        # Check portfolio percentage limit
        if self.portfolio_value > 0:
            position_pct = position_value / self.portfolio_value
            if position_pct > self.params.max_position_pct:
                return {
                    'approved': False,
                    'reason': f'Position {position_pct*100:.2f}% of portfolio exceeds limit {self.params.max_position_pct*100:.1f}%'
                }
        
        # Check for existing position in same symbol
        if symbol in self.open_positions:
            existing = self.open_positions[symbol]
            if existing['side'] != side:
                return {
                    'approved': False,
                    'reason': 'Conflicting position already open'
                }
        
        # Check correlation with existing positions
        # (simplified - in production would use actual correlation matrix)
        if len(self.open_positions) > 0:
            # Could add correlation check here
            pass
        
        return {'approved': True, 'reason': ''}
    
    def calculate_stop_loss(self, entry_price: float, side: str,
                           atr: float = None, support_resistance: Dict = None) -> float:
        """
        Calculate stop loss price based on multiple methods.
        
        Args:
            entry_price: Entry price of the trade
            side: LONG or SHORT
            atr: Average True Range for volatility-based stops
            support_resistance: Key support/resistance levels
        
        Returns:
            Stop loss price
        """
        if side == 'LONG':
            # Percentage-based stop
            sl_percentage = entry_price * (1 - self.params.stop_loss_pct / 100)
            
            # ATR-based stop (2x ATR below entry)
            sl_atr = entry_price - (atr * 2) if atr else sl_percentage
            
            # Support-based stop (below nearest support)
            sl_support = float('inf')
            if support_resistance and 'support' in support_resistance:
                for level in support_resistance['support']:
                    if level < entry_price:
                        sl_support = min(sl_support, level * 0.99)  # 1% below support
            
            # Take the tightest stop that's reasonable
            stops = [sl_percentage]
            if atr:
                stops.append(sl_atr)
            if sl_support != float('inf'):
                stops.append(sl_support)
            
            # Use the stop closest to entry but not too tight
            min_acceptable = entry_price * 0.95  # Max 5% stop
            valid_stops = [s for s in stops if s >= min_acceptable]
            
            return max(valid_stops) if valid_stops else sl_percentage
        
        else:  # SHORT
            sl_percentage = entry_price * (1 + self.params.stop_loss_pct / 100)
            sl_atr = entry_price + (atr * 2) if atr else sl_percentage
            
            sl_resistance = float('-inf')
            if support_resistance and 'resistance' in support_resistance:
                for level in support_resistance['resistance']:
                    if level > entry_price:
                        sl_resistance = max(sl_resistance, level * 1.01)  # 1% above resistance
            
            stops = [sl_percentage]
            if atr:
                stops.append(sl_atr)
            if sl_resistance != float('-inf'):
                stops.append(sl_resistance)
            
            max_acceptable = entry_price * 1.05  # Max 5% stop
            valid_stops = [s for s in stops if s <= max_acceptable]
            
            return min(valid_stops) if valid_stops else sl_percentage
    
    def calculate_take_profit(self, entry_price: float, side: str,
                             levels: int = 2) -> List[float]:
        """
        Calculate take profit levels.
        
        Args:
            entry_price: Entry price
            side: LONG or SHORT
            levels: Number of take profit levels
        
        Returns:
            List of take profit prices
        """
        profits = []
        
        for i in range(1, levels + 1):
            tp_pct = self.params.take_profit_pct * i / levels
            
            if side == 'LONG':
                tp = entry_price * (1 + tp_pct / 100)
            else:
                tp = entry_price * (1 - tp_pct / 100)
            
            profits.append(tp)
        
        return profits
    
    def update_position(self, symbol: str, side: str, quantity: float,
                       entry_price: float, stop_loss: float,
                       take_profits: List[float]):
        """Track an open position."""
        self.open_positions[symbol] = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profits': take_profits,
            'current_pnl': 0.0,
            'opened_at': None  # Set by caller
        }
    
    def close_position(self, symbol: str, exit_price: float, pnl: float):
        """Record a closed position."""
        if symbol in self.open_positions:
            position = self.open_positions.pop(symbol)
            position['exit_price'] = exit_price
            position['pnl'] = pnl
            
            self.trade_history.append(position)
            self.daily_pnl += pnl
    
    def reset_daily_pnl(self):
        """Reset daily PnL tracker (call at start of each trading day)."""
        self.daily_pnl = 0.0
    
    def get_risk_report(self) -> Dict:
        """Generate current risk status report."""
        total_exposure = sum(
            pos['quantity'] * pos['entry_price']
            for pos in self.open_positions.values()
        )
        
        unrealized_pnl = sum(
            pos.get('current_pnl', 0)
            for pos in self.open_positions.values()
        )
        
        return {
            'portfolio_value': self.portfolio_value,
            'total_exposure': total_exposure,
            'exposure_pct': total_exposure / self.portfolio_value * 100 if self.portfolio_value > 0 else 0,
            'open_positions': len(self.open_positions),
            'max_positions': self.params.max_open_positions,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': self.daily_pnl / self.portfolio_value * 100 if self.portfolio_value > 0 else 0,
            'unrealized_pnl': unrealized_pnl,
            'daily_loss_limit_remaining': self.params.max_daily_loss_usd + self.daily_pnl,
            'risk_utilization': {
                'position_size': total_exposure / self.params.max_position_size_usd if self.params.max_position_size_usd > 0 else 0,
                'daily_loss': abs(self.daily_pnl) / self.params.max_daily_loss_usd if self.params.max_daily_loss_usd > 0 else 0
            }
        }
    
    def emergency_close_all(self, current_prices: Dict[str, float]) -> List[Dict]:
        """
        Emergency close all positions (e.g., during extreme market conditions).
        
        Args:
            current_prices: Current prices for all open positions
        
        Returns:
            List of closed positions
        """
        closed = []
        
        for symbol, position in list(self.open_positions.items()):
            if symbol in current_prices:
                exit_price = current_prices[symbol]
                
                if position['side'] == 'LONG':
                    pnl = (exit_price - position['entry_price']) * position['quantity']
                else:
                    pnl = (position['entry_price'] - exit_price) * position['quantity']
                
                self.close_position(symbol, exit_price, pnl)
                closed.append({
                    'symbol': symbol,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'reason': 'EMERGENCY_CLOSE'
                })
        
        return closed
