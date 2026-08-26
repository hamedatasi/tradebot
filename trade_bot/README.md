# Advanced Crypto Trading Bot

A comprehensive cryptocurrency trading bot with support for multiple exchanges (Binance, Nobitex), AI-powered analysis, technical indicators, whale tracking, news sentiment analysis, and advanced risk management.

## Features

### 🔄 Exchange Integration
- **Binance**: Full API integration with testnet support
- **Nobitex**: Iranian exchange integration
- **Paper Trading**: Safe testing environment before live trading

### 📊 Technical Analysis
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- EMA/SMA (Exponential/Simple Moving Averages)
- ATR (Average True Range)
- VWAP (Volume Weighted Average Price)

### 🐋 Whale Detection
- Large trade identification
- Order book imbalance analysis
- Whale wall detection
- Accumulation/Distribution signals

### 📰 News & Sentiment Analysis
- USA economic news aggregation
- War/geopolitical news tracking
- Sentiment scoring (bullish/bearish/neutral)
- High-impact event detection
- Free API support (GNews, NewsAPI, CryptoPanic)

### 🤖 AI Trading Agent
- OpenAI-compatible endpoint integration
- Market analysis with reasoning
- Buy/Sell/Hold recommendations
- Entry price, stop-loss, take-profit suggestions
- Risk/reward ratio calculation
- Strategy vs AI comparison

### 📈 Strategy Manager
- Pre-built strategies:
  - Conservative (multiple confirmations required)
  - Balanced (medium risk)
  - Aggressive (early movement detection)
  - Whale Tracker (follow large players)
  - News Driven (sentiment-based)
- Custom strategy creation
- Signal source weighting
- Multiple aggregation methods

### 🔒 Risk Management
- Position sizing (Fixed, Percentage, Kelly, Volatility-based)
- Stop-loss calculation (percentage, ATR, support/resistance)
- Take-profit levels
- Daily loss limits
- Maximum position limits
- Portfolio exposure tracking
- Emergency close-all function

### 🧪 Backtesting Engine
- Historical data replay
- Realistic commission & slippage simulation
- Performance metrics:
  - Sharpe Ratio
  - Sortino Ratio
  - Win Rate
  - Profit Factor
  - Max Drawdown
- Parameter optimization (grid search)
- Equity curve tracking
- Detailed trade reports

## Installation

### Option 1: Quick Start with Web UI (Recommended)

**Windows:**
```cmd
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

This will automatically:
- Create a virtual environment
- Install all dependencies
- Create a `.env` configuration file
- Start the web interface at http://localhost:8000

### Option 2: Manual Installation

```bash
# Clone or copy the trade_bot directory to your project

# Install dependencies
pip install -r trade_bot/requirements.txt

# Optional: For full functionality
pip install openai pandas matplotlib
```

### Running the Web Interface Manually

```bash
cd trade_bot/web
python server.py
```

Then open your browser to **http://localhost:8000**

### Running the Bot Directly (CLI)

```bash
python -m trade_bot.core.bot
```

## Configuration

Create a `config.json` file or set environment variables:

```json
{
  "binance": {
    "api_key": "your_binance_api_key",
    "api_secret": "your_binance_api_secret",
    "sandbox": true
  },
  "nobitex": {
    "api_key": "your_nobitex_token",
    "api_secret": "",
    "sandbox": true
  },
  "news": {
    "gnews_api_key": "your_gnews_key",
    "newsapi_key": "your_newsapi_key"
  },
  "ai": {
    "openai_api_key": "your_openai_key",
    "openai_base_url": "https://api.openai.com/v1",
    "model_name": "gpt-3.5-turbo"
  },
  "risk": {
    "max_position_size": 1000,
    "stop_loss_pct": 2.0,
    "take_profit_pct": 5.0,
    "max_daily_loss": 500,
    "max_open_positions": 5
  },
  "paper_trading": true
}
```

Or use environment variables:
```bash
export BINANCE_API_KEY=your_key
export BINANCE_API_SECRET=your_secret
export NOBITEX_API_KEY=your_token
export GNEWS_API_KEY=your_gnews_key
export OPENAI_API_KEY=your_openai_key
```

## Usage

### Basic Example

```python
from trade_bot.core.bot import TradingBot

# Initialize bot
bot = TradingBot()

# Add symbols to track
bot.add_symbol("BTCUSDT", "binance")
bot.add_symbol("ETHUSDT", "binance")

# Set strategy
bot.set_strategy("balanced")

# Get analysis
analysis = bot.analyze_symbol("BTCUSDT")
print(f"Signal: {analysis['aggregated_signal']['action']}")
print(f"Confidence: {analysis['aggregated_signal']['confidence']*100:.1f}%")

# Execute paper trade
bot.execute_trade("BTCUSDT", "BUY", 0.001)

# Start auto-trading (paper mode by default)
bot.start_auto_trading(interval_minutes=15)
```

### Advanced Analysis

```python
from trade_bot.analyzers.technical import ChartAnalyzer
from trade_bot.connectors.exchanges import ExchangeManager

# Initialize components
exchange = ExchangeManager({}, {'api_key': '', 'api_secret': '', 'sandbox': True})
analyzer = ChartAnalyzer()

# Get historical data
candles = exchange.get_historical_data("BTCUSDT", "1h", limit=100)

# Analyze
analysis = analyzer.analyze(candles)

# View indicators
print(f"RSI: {analysis['indicators'].get('rsi', 'N/A')}")
print(f"MACD: {analysis['indicators'].get('macd', 'N/A')}")

# View detected patterns
for pattern in analysis.get('patterns', []):
    print(f"Pattern: {pattern['pattern']} -> {pattern['signal']}")

# View whale activity
if analysis.get('whale_activity'):
    print(f"Whale trades detected: {len(analysis['whale_activity'])}")
```

### Backtesting

```python
from trade_bot.backtest.engine import BacktestEngine
from trade_bot.analyzers.technical import ChartAnalyzer, Signal

# Initialize
engine = BacktestEngine(initial_capital=10000)
analyzer = ChartAnalyzer()

# Get historical data
candles = exchange.get_historical_data("BTCUSDT", "1h", limit=500)

# Generate signals from analysis
analysis = analyzer.analyze(candles)
signals = analysis.get('signals', [])

# Run backtest
result = engine.run(
    candles=candles,
    signals=signals,
    stop_loss_pct=2.0,
    take_profit_pct=5.0
)

# View results
print(engine.generate_report(result))

# Save results
engine.save_results(result, "backtest_results.json")
```

### AI Analysis

```python
from trade_bot.ai_agent.agent import TradingAI

# Initialize AI agent
ai = TradingAI(
    api_key="your_openai_key",
    base_url="https://api.openai.com/v1",
    model="gpt-3.5-turbo"
)

# Get market analysis
recommendation = ai.analyze_market(
    symbol="BTC/USDT",
    technical_data=analysis,
    news_sentiment=news_data,
    whale_activity=whale_trades
)

# View recommendation
print(f"Recommendation: {recommendation['recommendation']}")
print(f"Confidence: {recommendation['confidence']*100:.1f}%")
print(f"Reasoning: {recommendation['reasoning']}")

# Get human-readable explanation
explanation = ai.explain_decision(recommendation, analysis)
print(explanation)
```

### Custom Strategy

```python
from trade_bot.strategies.manager import StrategyManager, StrategyConfig, SignalWeight, SignalSource

manager = StrategyManager()

# Create custom strategy
custom_strategy = StrategyConfig(
    name="my_custom",
    description="My custom trading strategy",
    signal_weights=[
        SignalWeight(SignalSource.RSI, weight=2.0, enabled=True, min_strength=0.6),
        SignalWeight(SignalSource.WHALE_ACTIVITY, weight=3.0, enabled=True),
        SignalWeight(SignalSource.NEWS_SENTIMENT, weight=1.5, enabled=True),
    ],
    aggregation_method="weighted_average",
    buy_threshold=0.65,
    sell_threshold=-0.65
)

# Add and activate
manager.create_custom_strategy("my_custom", custom_strategy)
manager.set_active_strategy("my_custom")
```

## Architecture

```
trade_bot/
├── core/
│   ├── config.py       # Configuration management
│   └── bot.py          # Main bot orchestrator
├── connectors/
│   └── exchanges.py    # Exchange API connectors
├── analyzers/
│   ├── news.py         # News aggregation & sentiment
│   └── technical.py    # Technical analysis & patterns
├── strategies/
│   └── manager.py      # Strategy management
├── backtest/
│   └── engine.py       # Backtesting engine
├── ai_agent/
│   └── agent.py        # AI trading recommendations
└── utils/
    └── risk_manager.py # Risk management
```

## Safety Features

1. **Paper Trading Default**: Always starts in paper trading mode
2. **Risk Limits**: Configurable position sizes, daily loss limits
3. **Stop Loss**: Automatic stop-loss calculation
4. **Emergency Close**: Function to close all positions immediately
5. **Sandbox Mode**: Testnet support for Binance

## Important Notes

⚠️ **Trading cryptocurrencies involves significant risk.** This bot is provided for educational purposes. Always:
- Start with paper trading
- Test thoroughly before using real funds
- Never risk more than you can afford to lose
- Monitor the bot regularly
- Understand the strategies you're using

## License

MIT License - Use at your own risk.

## Contributing

Contributions welcome! Please ensure all features include:
- Proper error handling
- Documentation
- Paper trading support
- Risk management considerations
