"""
Advanced Strategy Manager for configuring and combining trading signals.
Allows users to select which indicators, patterns, and data sources to consider.
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json


class SignalSource(Enum):
    """Available signal sources."""
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"
    EMA = "ema"
    SMA = "sma"
    PATTERNS = "patterns"
    WHALE_ACTIVITY = "whale_activity"
    ORDER_BOOK = "order_book"
    NEWS_SENTIMENT = "news_sentiment"
    PRICE_ACTION = "price_action"
    VOLUME = "volume"


class AggregationMethod(Enum):
    """Methods to aggregate multiple signals."""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    CONSERVATIVE = "conservative"  # All must agree
    AGGRESSIVE = "aggressive"  # Any strong signal triggers


@dataclass
class SignalWeight:
    """Weight configuration for a signal source."""
    source: SignalSource
    weight: float = 1.0
    enabled: bool = True
    min_strength: float = 0.5  # Minimum strength to consider


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy."""
    name: str
    description: str = ""
    signal_weights: List[SignalWeight] = field(default_factory=list)
    aggregation_method: AggregationMethod = AggregationMethod.WEIGHTED_AVERAGE
    buy_threshold: float = 0.6  # Minimum score to trigger BUY
    sell_threshold: float = -0.6  # Maximum score to trigger SELL
    timeframes: List[str] = field(default_factory=lambda: ["1h"])
    symbols: List[str] = field(default_factory=list)
    risk_parameters: Dict = field(default_factory=dict)


class StrategyManager:
    """
    Advanced strategy manager that allows dynamic configuration of signal sources
    and combination methods.
    """
    
    def __init__(self):
        self.strategies: Dict[str, StrategyConfig] = {}
        self.active_strategy: Optional[str] = None
        self.custom_signals: Dict[str, Callable] = {}
        
        # Load default strategies
        self._load_default_strategies()
    
    def _load_default_strategies(self):
        """Load pre-configured default strategies."""
        
        # Conservative Strategy
        conservative = StrategyConfig(
            name="conservative",
            description="Low-risk strategy requiring multiple confirmations",
            signal_weights=[
                SignalWeight(SignalSource.RSI, weight=1.5, enabled=True, min_strength=0.6),
                SignalWeight(SignalSource.MACD, weight=1.5, enabled=True, min_strength=0.6),
                SignalWeight(SignalSource.PATTERNS, weight=2.0, enabled=True, min_strength=0.7),
                SignalWeight(SignalSource.WHALE_ACTIVITY, weight=1.0, enabled=True, min_strength=0.8),
                SignalWeight(SignalSource.NEWS_SENTIMENT, weight=0.5, enabled=False),
            ],
            aggregation_method=AggregationMethod.CONSERVATIVE,
            buy_threshold=0.7,
            sell_threshold=-0.7
        )
        self.strategies["conservative"] = conservative
        
        # Balanced Strategy
        balanced = StrategyConfig(
            name="balanced",
            description="Medium-risk balanced approach",
            signal_weights=[
                SignalWeight(SignalSource.RSI, weight=1.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.MACD, weight=1.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.BOLLINGER, weight=1.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.PATTERNS, weight=1.5, enabled=True, min_strength=0.6),
                SignalWeight(SignalSource.WHALE_ACTIVITY, weight=1.5, enabled=True, min_strength=0.6),
                SignalWeight(SignalSource.NEWS_SENTIMENT, weight=0.8, enabled=True, min_strength=0.4),
            ],
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
            buy_threshold=0.6,
            sell_threshold=-0.6
        )
        self.strategies["balanced"] = balanced
        
        # Aggressive Strategy
        aggressive = StrategyConfig(
            name="aggressive",
            description="High-risk strategy catching early movements",
            signal_weights=[
                SignalWeight(SignalSource.RSI, weight=0.8, enabled=True, min_strength=0.4),
                SignalWeight(SignalSource.MACD, weight=0.8, enabled=True, min_strength=0.4),
                SignalWeight(SignalSource.WHALE_ACTIVITY, weight=2.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.ORDER_BOOK, weight=1.5, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.PATTERNS, weight=1.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.NEWS_SENTIMENT, weight=1.0, enabled=True, min_strength=0.3),
            ],
            aggregation_method=AggregationMethod.AGGRESSIVE,
            buy_threshold=0.5,
            sell_threshold=-0.5
        )
        self.strategies["aggressive"] = aggressive
        
        # Whale Tracker Strategy
        whale_tracker = StrategyConfig(
            name="whale_tracker",
            description="Focus on detecting and following whale movements",
            signal_weights=[
                SignalWeight(SignalSource.WHALE_ACTIVITY, weight=3.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.ORDER_BOOK, weight=2.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.VOLUME, weight=1.5, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.PATTERNS, weight=1.0, enabled=True, min_strength=0.5),
            ],
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
            buy_threshold=0.55,
            sell_threshold=-0.55
        )
        self.strategies["whale_tracker"] = whale_tracker
        
        # News Driven Strategy
        news_driven = StrategyConfig(
            name="news_driven",
            description="React to news and market sentiment",
            signal_weights=[
                SignalWeight(SignalSource.NEWS_SENTIMENT, weight=2.5, enabled=True, min_strength=0.4),
                SignalWeight(SignalSource.RSI, weight=1.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.MACD, weight=1.0, enabled=True, min_strength=0.5),
                SignalWeight(SignalSource.VOLUME, weight=1.5, enabled=True, min_strength=0.5),
            ],
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
            buy_threshold=0.55,
            sell_threshold=-0.55
        )
        self.strategies["news_driven"] = news_driven
    
    def create_custom_strategy(self, name: str, config: StrategyConfig) -> bool:
        """Create a custom strategy."""
        if name in self.strategies:
            print(f"Strategy '{name}' already exists. Use update instead.")
            return False
        
        self.strategies[name] = config
        return True
    
    def update_strategy(self, name: str, **kwargs) -> bool:
        """Update an existing strategy's configuration."""
        if name not in self.strategies:
            print(f"Strategy '{name}' not found.")
            return False
        
        strategy = self.strategies[name]
        
        for key, value in kwargs.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
            else:
                print(f"Warning: Unknown strategy attribute '{key}'")
        
        return True
    
    def enable_signal_source(self, strategy_name: str, source: SignalSource, 
                            weight: float = 1.0) -> bool:
        """Enable a signal source for a strategy."""
        if strategy_name not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_name]
        
        # Check if source already exists
        for sw in strategy.signal_weights:
            if sw.source == source:
                sw.enabled = True
                sw.weight = weight
                return True
        
        # Add new signal weight
        strategy.signal_weights.append(SignalWeight(source, weight=weight, enabled=True))
        return True
    
    def disable_signal_source(self, strategy_name: str, source: SignalSource) -> bool:
        """Disable a signal source for a strategy."""
        if strategy_name not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_name]
        
        for sw in strategy.signal_weights:
            if sw.source == source:
                sw.enabled = False
                return True
        
        return False
    
    def set_active_strategy(self, strategy_name: str) -> bool:
        """Set the currently active strategy."""
        if strategy_name not in self.strategies:
            print(f"Strategy '{strategy_name}' not found.")
            return False
        
        self.active_strategy = strategy_name
        print(f"Active strategy set to: {strategy_name}")
        return True
    
    def get_active_strategy(self) -> Optional[StrategyConfig]:
        """Get the currently active strategy."""
        if self.active_strategy and self.active_strategy in self.strategies:
            return self.strategies[self.active_strategy]
        return None
    
    def list_strategies(self) -> List[str]:
        """List all available strategies."""
        return list(self.strategies.keys())
    
    def get_strategy_details(self, name: str) -> Optional[Dict]:
        """Get detailed information about a strategy."""
        if name not in self.strategies:
            return None
        
        strategy = self.strategies[name]
        return {
            'name': strategy.name,
            'description': strategy.description,
            'signal_weights': [
                {
                    'source': sw.source.value,
                    'weight': sw.weight,
                    'enabled': sw.enabled,
                    'min_strength': sw.min_strength
                }
                for sw in strategy.signal_weights
            ],
            'aggregation_method': strategy.aggregation_method.value,
            'buy_threshold': strategy.buy_threshold,
            'sell_threshold': strategy.sell_threshold,
            'timeframes': strategy.timeframes,
            'symbols': strategy.symbols
        }
    
    def add_custom_signal(self, name: str, signal_func: Callable) -> bool:
        """
        Add a custom signal generator function.
        Function should accept analysis data and return Signal objects.
        """
        self.custom_signals[name] = signal_func
        return True
    
    def aggregate_signals(self, signals: List, strategy: StrategyConfig = None) -> Dict:
        """
        Aggregate multiple signals according to strategy configuration.
        Returns final decision with confidence score.
        """
        if not strategy:
            strategy = self.get_active_strategy()
        
        if not strategy:
            # Default aggregation
            return self._simple_aggregation(signals)
        
        if not signals:
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'reason': 'No signals available'
            }
        
        # Filter signals by enabled sources and minimum strength
        enabled_sources = {sw.source for sw in strategy.signal_weights if sw.enabled}
        source_weights = {sw.source: sw for sw in strategy.signal_weights}
        
        filtered_signals = []
        for signal in signals:
            # Map signal source to enum
            source_enum = self._map_source_to_enum(signal.source)
            
            if source_enum not in enabled_sources:
                continue
            
            weight_config = source_weights.get(source_enum)
            if weight_config and signal.strength >= weight_config.min_strength:
                filtered_signals.append((signal, weight_config))
        
        if not filtered_signals:
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'reason': 'No signals meet criteria'
            }
        
        # Apply aggregation method
        if strategy.aggregation_method == AggregationMethod.MAJORITY_VOTE:
            return self._majority_vote(filtered_signals)
        elif strategy.aggregation_method == AggregationMethod.WEIGHTED_AVERAGE:
            return self._weighted_average(filtered_signals, strategy)
        elif strategy.aggregation_method == AggregationMethod.CONSERVATIVE:
            return self._conservative(filtered_signals, strategy)
        elif strategy.aggregation_method == AggregationMethod.AGGRESSIVE:
            return self._aggressive(filtered_signals, strategy)
        
        return self._simple_aggregation([s[0] for s in filtered_signals])
    
    def _map_source_to_enum(self, source_str: str) -> Optional[SignalSource]:
        """Map string source to SignalSource enum."""
        try:
            return SignalSource(source_str.lower())
        except ValueError:
            # Try partial match
            source_lower = source_str.lower()
            for src in SignalSource:
                if src.value in source_lower or source_lower in src.value:
                    return src
        return None
    
    def _simple_aggregation(self, signals: List) -> Dict:
        """Simple majority vote without weights."""
        buy_count = sum(1 for s in signals if s.action == 'BUY')
        sell_count = sum(1 for s in signals if s.action == 'SELL')
        
        total = len(signals)
        if total == 0:
            return {'action': 'HOLD', 'confidence': 0.0}
        
        avg_strength = sum(s.strength for s in signals) / total
        
        if buy_count > sell_count:
            return {'action': 'BUY', 'confidence': avg_strength, 'buy_signals': buy_count, 'sell_signals': sell_count}
        elif sell_count > buy_count:
            return {'action': 'SELL', 'confidence': avg_strength, 'buy_signals': buy_count, 'sell_signals': sell_count}
        else:
            return {'action': 'HOLD', 'confidence': 0.0}
    
    def _weighted_average(self, signals_with_weights: List, strategy: StrategyConfig) -> Dict:
        """Calculate weighted average of signals."""
        total_score = 0.0
        total_weight = 0.0
        
        for signal, weight_config in signals_with_weights:
            signal_value = 1 if signal.action == 'BUY' else (-1 if signal.action == 'SELL' else 0)
            weighted_value = signal_value * signal.strength * weight_config.weight
            
            total_score += weighted_value
            total_weight += weight_config.weight
        
        if total_weight == 0:
            return {'action': 'HOLD', 'confidence': 0.0}
        
        normalized_score = total_score / total_weight
        
        if normalized_score > strategy.buy_threshold:
            return {'action': 'BUY', 'confidence': abs(normalized_score)}
        elif normalized_score < strategy.sell_threshold:
            return {'action': 'SELL', 'confidence': abs(normalized_score)}
        else:
            return {'action': 'HOLD', 'confidence': abs(normalized_score)}
    
    def _conservative(self, signals_with_weights: List, strategy: StrategyConfig) -> Dict:
        """Conservative: require all signals to agree."""
        if not signals_with_weights:
            return {'action': 'HOLD', 'confidence': 0.0}
        
        actions = set(signal.action for signal, _ in signals_with_weights)
        
        if len(actions) > 1:
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': 'Conflicting signals'}
        
        action = actions.pop()
        avg_strength = sum(signal.strength for signal, _ in signals_with_weights) / len(signals_with_weights)
        
        if action == 'BUY' and avg_strength >= strategy.buy_threshold:
            return {'action': 'BUY', 'confidence': avg_strength}
        elif action == 'SELL' and avg_strength >= abs(strategy.sell_threshold):
            return {'action': 'SELL', 'confidence': avg_strength}
        else:
            return {'action': 'HOLD', 'confidence': avg_strength}
    
    def _aggressive(self, signals_with_weights: List, strategy: StrategyConfig) -> Dict:
        """Aggressive: any strong signal triggers action."""
        for signal, weight_config in signals_with_weights:
            if signal.strength >= 0.7:  # Strong signal threshold
                if signal.action == 'BUY':
                    return {'action': 'BUY', 'confidence': signal.strength, 'source': signal.source}
                elif signal.action == 'SELL':
                    return {'action': 'SELL', 'confidence': signal.strength, 'source': signal.source}
        
        # Fall back to weighted average if no strong signals
        return self._weighted_average(signals_with_weights, strategy)
    
    def export_strategy(self, name: str, filename: str) -> bool:
        """Export strategy configuration to JSON file."""
        if name not in self.strategies:
            return False
        
        details = self.get_strategy_details(name)
        with open(filename, 'w') as f:
            json.dump(details, f, indent=2)
        
        return True
    
    def import_strategy(self, filename: str) -> bool:
        """Import strategy configuration from JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Convert back to StrategyConfig
            signal_weights = []
            for sw_data in data.get('signal_weights', []):
                source = SignalSource(sw_data['source'])
                signal_weights.append(SignalWeight(
                    source=source,
                    weight=sw_data['weight'],
                    enabled=sw_data['enabled'],
                    min_strength=sw_data['min_strength']
                ))
            
            strategy = StrategyConfig(
                name=data['name'],
                description=data.get('description', ''),
                signal_weights=signal_weights,
                aggregation_method=AggregationMethod(data.get('aggregation_method', 'weighted_average')),
                buy_threshold=data.get('buy_threshold', 0.6),
                sell_threshold=data.get('sell_threshold', -0.6),
                timeframes=data.get('timeframes', ['1h']),
                symbols=data.get('symbols', [])
            )
            
            self.strategies[data['name']] = strategy
            return True
        except Exception as e:
            print(f"Error importing strategy: {e}")
            return False
