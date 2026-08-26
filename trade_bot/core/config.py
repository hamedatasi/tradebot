"""
Configuration management for the trading bot.
Handles API keys, risk parameters, and system settings.
"""
import os
from dataclasses import dataclass
from typing import Optional, List
import json


@dataclass
class ExchangeConfig:
    """Exchange API configuration."""
    api_key: str = ""
    api_secret: str = ""
    sandbox: bool = True  # Use testnet by default


@dataclass
class RiskConfig:
    """Risk management configuration."""
    max_position_size: float = 1000.0  # Max position in USD
    stop_loss_pct: float = 2.0  # Stop loss percentage
    take_profit_pct: float = 5.0  # Take profit percentage
    max_daily_loss: float = 500.0  # Max daily loss in USD
    position_sizing_method: str = "fixed"  # fixed, kelly, volatility
    leverage: float = 1.0
    max_open_positions: int = 5


@dataclass
class NewsConfig:
    """News API configuration."""
    gnews_api_key: str = ""  # Free tier available
    newsapi_key: str = ""  # Free tier available
    update_interval_minutes: int = 15
    sentiment_threshold: float = 0.3  # Threshold for actionable news


@dataclass
class AIConfig:
    """AI/LLM configuration."""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000


@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_capital: float = 10000.0
    commission_rate: float = 0.001  # 0.1% per trade
    slippage_rate: float = 0.0005  # 0.05% slippage
    start_date: str = "2023-01-01"
    end_date: str = "2024-01-01"


@dataclass
class StrategyConfig:
    """Strategy manager configuration."""
    enabled_indicators: List[str] = None
    enabled_patterns: List[str] = None
    whale_tracking: bool = True
    news_sentiment: bool = True
    technical_analysis: bool = True
    price_action: bool = True
    
    def __post_init__(self):
        if self.enabled_indicators is None:
            self.enabled_indicators = ["RSI", "MACD", "EMA", "Bollinger"]
        if self.enabled_patterns is None:
            self.enabled_patterns = ["head_and_shoulders", "double_top", "breakout"]


class ConfigManager:
    """Central configuration manager."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.exchange_nobitex = ExchangeConfig()
        self.exchange_binance = ExchangeConfig()
        self.risk = RiskConfig()
        self.news = NewsConfig()
        self.ai = AIConfig()
        self.backtest = BacktestConfig()
        self.strategy = StrategyConfig()
        self.paper_trading = True  # Default to paper trading
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file or environment variables."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                self._apply_config(config_data)
        else:
            # Load from environment variables
            self._load_from_env()
    
    def _apply_config(self, config_data: dict):
        """Apply configuration from dictionary."""
        if 'nobitex' in config_data:
            self.exchange_nobitex = ExchangeConfig(**config_data['nobitex'])
        if 'binance' in config_data:
            self.exchange_binance = ExchangeConfig(**config_data['binance'])
        if 'risk' in config_data:
            self.risk = RiskConfig(**config_data['risk'])
        if 'news' in config_data:
            self.news = NewsConfig(**config_data['news'])
        if 'ai' in config_data:
            self.ai = AIConfig(**config_data['ai'])
        if 'backtest' in config_data:
            self.backtest = BacktestConfig(**config_data['backtest'])
        if 'strategy' in config_data:
            self.strategy = StrategyConfig(**config_data['strategy'])
        if 'paper_trading' in config_data:
            self.paper_trading = config_data['paper_trading']
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        self.exchange_nobitex.api_key = os.getenv('NOBITEX_API_KEY', '')
        self.exchange_nobitex.api_secret = os.getenv('NOBITEX_API_SECRET', '')
        self.exchange_binance.api_key = os.getenv('BINANCE_API_KEY', '')
        self.exchange_binance.api_secret = os.getenv('BINANCE_API_SECRET', '')
        self.news.gnews_api_key = os.getenv('GNEWS_API_KEY', '')
        self.news.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        self.ai.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.ai.openai_base_url = os.getenv('OPENAI_BASE_URL', self.ai.openai_base_url)
    
    def save_config(self):
        """Save current configuration to file."""
        config_data = {
            'nobitex': {
                'api_key': self.exchange_nobitex.api_key,
                'api_secret': self.exchange_nobitex.api_secret,
                'sandbox': self.exchange_nobitex.sandbox
            },
            'binance': {
                'api_key': self.exchange_binance.api_key,
                'api_secret': self.exchange_binance.api_secret,
                'sandbox': self.exchange_binance.sandbox
            },
            'risk': {
                'max_position_size': self.risk.max_position_size,
                'stop_loss_pct': self.risk.stop_loss_pct,
                'take_profit_pct': self.risk.take_profit_pct,
                'max_daily_loss': self.risk.max_daily_loss,
                'position_sizing_method': self.risk.position_sizing_method,
                'leverage': self.risk.leverage,
                'max_open_positions': self.risk.max_open_positions
            },
            'news': {
                'gnews_api_key': self.news.gnews_api_key,
                'newsapi_key': self.news.newsapi_key,
                'update_interval_minutes': self.news.update_interval_minutes,
                'sentiment_threshold': self.news.sentiment_threshold
            },
            'ai': {
                'openai_api_key': self.ai.openai_api_key,
                'openai_base_url': self.ai.openai_base_url,
                'model_name': self.ai.model_name,
                'temperature': self.ai.temperature,
                'max_tokens': self.ai.max_tokens
            },
            'backtest': {
                'initial_capital': self.backtest.initial_capital,
                'commission_rate': self.backtest.commission_rate,
                'slippage_rate': self.backtest.slippage_rate,
                'start_date': self.backtest.start_date,
                'end_date': self.backtest.end_date
            },
            'strategy': {
                'enabled_indicators': self.strategy.enabled_indicators,
                'enabled_patterns': self.strategy.enabled_patterns,
                'whale_tracking': self.strategy.whale_tracking,
                'news_sentiment': self.strategy.news_sentiment,
                'technical_analysis': self.strategy.technical_analysis,
                'price_action': self.strategy.price_action
            },
            'paper_trading': self.paper_trading
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading mode is enabled."""
        return self.paper_trading
    
    def toggle_paper_trading(self):
        """Toggle between paper and live trading."""
        self.paper_trading = not self.paper_trading
        print(f"Trading mode switched to: {'Paper' if self.paper_trading else 'LIVE'}")


# Global config instance
config = ConfigManager()
