"""
Technical analysis module with multiple indicators and chart pattern recognition.
Supports whale activity detection and price action analysis.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Signal:
    """Trading signal structure."""
    symbol: str
    action: str  # BUY, SELL, HOLD
    strength: float  # 0-1 confidence
    source: str  # Which indicator/pattern generated this
    timestamp: int
    price: float
    metadata: Dict = None


class TechnicalIndicators:
    """Calculate various technical indicators."""
    
    @staticmethod
    def sma(data: List[float], period: int = 20) -> List[float]:
        """Simple Moving Average."""
        if len(data) < period:
            return []
        
        result = []
        for i in range(len(data)):
            if i < period - 1:
                result.append(None)
            else:
                avg = sum(data[i-period+1:i+1]) / period
                result.append(avg)
        return result
    
    @staticmethod
    def ema(data: List[float], period: int = 20) -> List[float]:
        """Exponential Moving Average."""
        if len(data) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema_values = [sum(data[:period]) / period]
        
        for i in range(period, len(data)):
            ema = (data[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)
        
        return [None] * (period - 1) + ema_values
    
    @staticmethod
    def rsi(data: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index."""
        if len(data) < period + 1:
            return []
        
        gains = []
        losses = []
        
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi_values = []
        
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))
        
        return [None] * (period - 1) + rsi_values
    
    @staticmethod
    def macd(data: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """MACD indicator."""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        
        if len(ema_fast) < len(ema_slow):
            ema_fast = [None] * (len(ema_slow) - len(ema_fast)) + ema_fast[1:]
        
        macd_line = []
        for i in range(len(ema_fast)):
            if ema_fast[i] is None or ema_slow[i] is None:
                macd_line.append(None)
            else:
                macd_line.append(ema_fast[i] - ema_slow[i])
        
        # Calculate signal line (EMA of MACD line)
        macd_valid = [x for x in macd_line if x is not None]
        if len(macd_valid) < signal:
            return {'macd': macd_line, 'signal': [], 'histogram': []}
        
        signal_line = TechnicalIndicators.ema(macd_valid, signal)
        signal_line = [None] * (len(macd_line) - len(signal_line)) + signal_line
        
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is None or signal_line[i] is None:
                histogram.append(None)
            else:
                histogram.append(macd_line[i] - signal_line[i])
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, std_dev: float = 2.0) -> Dict:
        """Bollinger Bands."""
        sma = TechnicalIndicators.sma(data, period)
        
        upper = []
        lower = []
        
        for i in range(len(data)):
            if sma[i] is None or i < period - 1:
                upper.append(None)
                lower.append(None)
            else:
                window = data[i-period+1:i+1]
                std = np.std(window)
                upper.append(sma[i] + std_dev * std)
                lower.append(sma[i] - std_dev * std)
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """Average True Range for volatility measurement."""
        if len(highs) < period + 1:
            return []
        
        tr_values = []
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr_values.append(max(tr1, tr2, tr3))
        
        atr_values = [sum(tr_values[:period]) / period]
        
        for i in range(period, len(tr_values)):
            atr = (atr_values[-1] * (period - 1) + tr_values[i]) / period
            atr_values.append(atr)
        
        return [None] * period + atr_values
    
    @staticmethod
    def vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> List[float]:
        """Volume Weighted Average Price."""
        vwap_values = []
        cumulative_tp_vol = 0
        cumulative_vol = 0
        
        for i in range(len(closes)):
            typical_price = (highs[i] + lows[i] + closes[i]) / 3
            cumulative_tp_vol += typical_price * volumes[i]
            cumulative_vol += volumes[i]
            
            if cumulative_vol > 0:
                vwap_values.append(cumulative_tp_vol / cumulative_vol)
            else:
                vwap_values.append(None)
        
        return vwap_values


class WhaleDetector:
    """Detect whale activities from trade data."""
    
    def __init__(self, threshold_multiplier: float = 5.0):
        self.threshold_multiplier = threshold_multiplier
    
    def detect_whale_trades(self, trades: List[Dict], avg_volume: float = None) -> List[Dict]:
        """
        Detect unusually large trades that might indicate whale activity.
        Trades should have: timestamp, price, quantity, side
        """
        if not trades:
            return []
        
        if avg_volume is None:
            quantities = [trade.get('quantity', 0) for trade in trades]
            avg_volume = np.mean(quantities)
        
        threshold = avg_volume * self.threshold_multiplier
        
        whale_trades = []
        for trade in trades:
            quantity = trade.get('quantity', 0)
            if quantity > threshold:
                whale_trades.append({
                    **trade,
                    'whale_score': quantity / avg_volume,
                    'is_buy': trade.get('side', '').upper() == 'BUY',
                    'impact_estimate': quantity / avg_volume * 0.01  # Estimated price impact %
                })
        
        return whale_trades
    
    def analyze_order_book_imbalance(self, order_book: Dict, depth: int = 10) -> Dict:
        """
        Analyze order book for whale walls.
        Order book should have: bids [[price, qty], ...], asks [[price, qty], ...]
        """
        bids = order_book.get('bids', [])[:depth]
        asks = order_book.get('asks', [])[:depth]
        
        total_bid_volume = sum(bid[1] for bid in bids)
        total_ask_volume = sum(ask[1] for ask in asks)
        
        # Find largest single orders
        max_bid = max(bids, key=lambda x: x[1]) if bids else [0, 0]
        max_ask = max(asks, key=lambda x: x[1]) if asks else [0, 0]
        
        imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume + 1e-10)
        
        return {
            'bid_volume': total_bid_volume,
            'ask_volume': total_ask_volume,
            'imbalance': imbalance,
            'max_bid_wall': {'price': max_bid[0], 'quantity': max_bid[1]},
            'max_ask_wall': {'price': max_ask[0], 'quantity': max_ask[1]},
            'whale_presence': max_bid[1] > total_bid_volume * 0.3 or max_ask[1] > total_ask_volume * 0.3
        }


class PatternRecognizer:
    """Recognize chart patterns and price action signals."""
    
    def __init__(self):
        self.min_pattern_length = 5
    
    def detect_head_and_shoulders(self, highs: List[float], lows: List[float]) -> Optional[Dict]:
        """Detect head and shoulders pattern."""
        if len(highs) < self.min_pattern_length * 3:
            return None
        
        # Simplified detection - look for three peaks with middle highest
        for i in range(len(highs) - self.min_pattern_length * 2):
            left_shoulder = max(highs[i:i+self.min_pattern_length])
            head = max(highs[i+self.min_pattern_length:i+self.min_pattern_length*2])
            right_shoulder = max(highs[i+self.min_pattern_length*2:i+self.min_pattern_length*3])
            
            if left_shoulder < head and right_shoulder < head:
                if abs(left_shoulder - right_shoulder) / head < 0.1:  # Shoulders similar height
                    return {
                        'pattern': 'head_and_shoulders',
                        'type': 'reversal',
                        'signal': 'SELL',
                        'confidence': 0.7,
                        'neckline': min(lows[i:i+self.min_pattern_length*3]),
                        'target': head - (head - min(lows[i:i+self.min_pattern_length*3]))
                    }
        
        return None
    
    def detect_double_top_bottom(self, highs: List[float], lows: List[float]) -> Optional[Dict]:
        """Detect double top or double bottom pattern."""
        if len(highs) < self.min_pattern_length * 2:
            return None
        
        # Double Top
        for i in range(len(highs) - self.min_pattern_length * 2):
            top1 = max(highs[i:i+self.min_pattern_length])
            top2 = max(highs[i+self.min_pattern_length:i+self.min_pattern_length*2])
            
            if abs(top1 - top2) / top1 < 0.02:  # Tops within 2%
                return {
                    'pattern': 'double_top',
                    'type': 'reversal',
                    'signal': 'SELL',
                    'confidence': 0.65,
                    'resistance': top1,
                    'target': top1 - (top1 - min(lows[i:i+self.min_pattern_length*2]))
                }
        
        # Double Bottom
        for i in range(len(lows) - self.min_pattern_length * 2):
            bottom1 = min(lows[i:i+self.min_pattern_length])
            bottom2 = min(lows[i+self.min_pattern_length:i+self.min_pattern_length*2])
            
            if abs(bottom1 - bottom2) / bottom1 < 0.02:  # Bottoms within 2%
                return {
                    'pattern': 'double_bottom',
                    'type': 'reversal',
                    'signal': 'BUY',
                    'confidence': 0.65,
                    'support': bottom1,
                    'target': bottom1 + (max(highs[i:i+self.min_pattern_length*2]) - bottom1)
                }
        
        return None
    
    def detect_breakout(self, closes: List[float], volumes: List[float], 
                       period: int = 20) -> Optional[Dict]:
        """Detect breakout above resistance or below support."""
        if len(closes) < period * 2:
            return None
        
        recent_closes = closes[-period:]
        previous_closes = closes[-period*2:-period]
        
        resistance = max(previous_closes)
        support = min(previous_closes)
        
        current_price = closes[-1]
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-period:])
        
        # Bullish breakout
        if current_price > resistance and current_volume > avg_volume * 1.5:
            return {
                'pattern': 'breakout',
                'type': 'bullish',
                'signal': 'BUY',
                'confidence': min((current_volume / avg_volume - 1) * 0.5, 0.9),
                'resistance': resistance,
                'volume_confirmation': True
            }
        
        # Bearish breakdown
        if current_price < support and current_volume > avg_volume * 1.5:
            return {
                'pattern': 'breakdown',
                'type': 'bearish',
                'signal': 'SELL',
                'confidence': min((current_volume / avg_volume - 1) * 0.5, 0.9),
                'support': support,
                'volume_confirmation': True
            }
        
        return None


class ChartAnalyzer:
    """Main chart analysis engine combining all techniques."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.indicators = TechnicalIndicators()
        self.whale_detector = WhaleDetector()
        self.pattern_recognizer = PatternRecognizer()
    
    def analyze(self, candles: List[Dict], trades: List[Dict] = None, 
               order_book: Dict = None) -> Dict:
        """
        Perform comprehensive chart analysis.
        Candles should have: timestamp, open, high, low, close, volume
        """
        if not candles or len(candles) < 30:
            return {'error': 'Insufficient data'}
        
        # Extract OHLCV arrays
        opens = [c['open'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        # Calculate indicators
        analysis = {
            'timestamp': candles[-1]['timestamp'],
            'current_price': closes[-1],
            'indicators': {},
            'patterns': [],
            'whale_activity': [],
            'signals': []
        }
        
        # RSI
        rsi = self.indicators.rsi(closes, 14)
        if rsi and rsi[-1] is not None:
            analysis['indicators']['rsi'] = rsi[-1]
            if rsi[-1] < 30:
                analysis['signals'].append(Signal(
                    symbol='UNKNOWN',
                    action='BUY',
                    strength=0.6,
                    source='RSI_OVERSOLD',
                    timestamp=candles[-1]['timestamp'],
                    price=closes[-1]
                ))
            elif rsi[-1] > 70:
                analysis['signals'].append(Signal(
                    symbol='UNKNOWN',
                    action='SELL',
                    strength=0.6,
                    source='RSI_OVERBOUGHT',
                    timestamp=candles[-1]['timestamp'],
                    price=closes[-1]
                ))
        
        # MACD
        macd_data = self.indicators.macd(closes)
        if macd_data['histogram'] and macd_data['histogram'][-1] is not None:
            analysis['indicators']['macd'] = {
                'macd': macd_data['macd'][-1],
                'signal': macd_data['signal'][-1],
                'histogram': macd_data['histogram'][-1]
            }
            
            # MACD crossover signal
            if len(macd_data['histogram']) > 1:
                prev_hist = macd_data['histogram'][-2]
                curr_hist = macd_data['histogram'][-1]
                
                if prev_hist < 0 and curr_hist > 0:
                    analysis['signals'].append(Signal(
                        symbol='UNKNOWN',
                        action='BUY',
                        strength=0.7,
                        source='MACD_BULLISH_CROSSOVER',
                        timestamp=candles[-1]['timestamp'],
                        price=closes[-1]
                    ))
                elif prev_hist > 0 and curr_hist < 0:
                    analysis['signals'].append(Signal(
                        symbol='UNKNOWN',
                        action='SELL',
                        strength=0.7,
                        source='MACD_BEARISH_CROSSOVER',
                        timestamp=candles[-1]['timestamp'],
                        price=closes[-1]
                    ))
        
        # Bollinger Bands
        bb = self.indicators.bollinger_bands(closes, 20)
        if bb['upper'] and bb['upper'][-1] is not None:
            analysis['indicators']['bollinger'] = {
                'upper': bb['upper'][-1],
                'middle': bb['middle'][-1],
                'lower': bb['lower'][-1],
                'position': (closes[-1] - bb['lower'][-1]) / (bb['upper'][-1] - bb['lower'][-1])
            }
        
        # ATR (volatility)
        atr = self.indicators.atr(highs, lows, closes, 14)
        if atr and atr[-1] is not None:
            analysis['indicators']['atr'] = atr[-1]
        
        # VWAP
        vwap = self.indicators.vwap(highs, lows, closes, volumes)
        if vwap and vwap[-1] is not None:
            analysis['indicators']['vwap'] = vwap[-1]
        
        # Pattern recognition
        patterns = []
        
        hs_pattern = self.pattern_recognizer.detect_head_and_shoulders(highs, lows)
        if hs_pattern:
            patterns.append(hs_pattern)
        
        db_pattern = self.pattern_recognizer.detect_double_top_bottom(highs, lows)
        if db_pattern:
            patterns.append(db_pattern)
        
        breakout = self.pattern_recognizer.detect_breakout(closes, volumes, 20)
        if breakout:
            patterns.append(breakout)
        
        analysis['patterns'] = patterns
        
        # Convert patterns to signals
        for pattern in patterns:
            analysis['signals'].append(Signal(
                symbol='UNKNOWN',
                action=pattern['signal'],
                strength=pattern['confidence'],
                source=f"PATTERN_{pattern['pattern'].upper()}",
                timestamp=candles[-1]['timestamp'],
                price=closes[-1],
                metadata=pattern
            ))
        
        # Whale detection
        if trades:
            whale_trades = self.whale_detector.detect_whale_trades(trades)
            if whale_trades:
                analysis['whale_activity'] = whale_trades
                
                # Generate signal based on whale activity
                recent_whales = whale_trades[-5:]  # Last 5 whale trades
                buy_pressure = sum(1 for t in recent_whales if t['is_buy'])
                
                if buy_pressure >= 3:
                    analysis['signals'].append(Signal(
                        symbol='UNKNOWN',
                        action='BUY',
                        strength=0.8,
                        source='WHALE_ACCUMULATION',
                        timestamp=candles[-1]['timestamp'],
                        price=closes[-1],
                        metadata={'whale_trades': len(recent_whales)}
                    ))
                elif buy_pressure <= 2:
                    analysis['signals'].append(Signal(
                        symbol='UNKNOWN',
                        action='SELL',
                        strength=0.8,
                        source='WHALE_DISTRIBUTION',
                        timestamp=candles[-1]['timestamp'],
                        price=closes[-1],
                        metadata={'whale_trades': len(recent_whales)}
                    ))
        
        # Order book analysis
        if order_book:
            ob_analysis = self.whale_detector.analyze_order_book_imbalance(order_book)
            analysis['order_book'] = ob_analysis
            
            if ob_analysis['whale_presence']:
                if ob_analysis['imbalance'] > 0.3:
                    analysis['signals'].append(Signal(
                        symbol='UNKNOWN',
                        action='BUY',
                        strength=0.5,
                        source='ORDER_BOOK_IMBALANCE',
                        timestamp=candles[-1]['timestamp'],
                        price=closes[-1],
                        metadata=ob_analysis
                    ))
                elif ob_analysis['imbalance'] < -0.3:
                    analysis['signals'].append(Signal(
                        symbol='UNKNOWN',
                        action='SELL',
                        strength=0.5,
                        source='ORDER_BOOK_IMBALANCE',
                        timestamp=candles[-1]['timestamp'],
                        price=closes[-1],
                        metadata=ob_analysis
                    ))
        
        return analysis
