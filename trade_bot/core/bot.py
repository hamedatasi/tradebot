"""
Main trading bot engine that orchestrates all components.
Handles auto-trading, paper trading, and signal execution.
"""
import time
from typing import Dict, List, Optional
from datetime import datetime
import threading

# Import all components
from trade_bot.core.config import ConfigManager, config
from trade_bot.connectors.exchanges import ExchangeManager
from trade_bot.analyzers.news import NewsAggregator
from trade_bot.analyzers.technical import ChartAnalyzer, Signal
from trade_bot.strategies.manager import StrategyManager
from trade_bot.backtest.engine import BacktestEngine
from trade_bot.ai_agent.agent import TradingAI
from trade_bot.utils.risk_manager import RiskManager, RiskParameters


class TradingBot:
    """
    Main trading bot that coordinates all components for automated trading.
    """
    
    def __init__(self, config_manager: ConfigManager = None):
        self.config = config_manager or config
        
        # Initialize components
        self.exchange_manager = ExchangeManager(
            nobitex_config={
                'api_key': self.config.exchange_nobitex.api_key,
                'api_secret': self.config.exchange_nobitex.api_secret,
                'sandbox': self.config.exchange_nobitex.sandbox
            },
            binance_config={
                'api_key': self.config.exchange_binance.api_key,
                'api_secret': self.config.exchange_binance.api_secret,
                'sandbox': self.config.exchange_binance.sandbox
            }
        )
        
        self.news_aggregator = NewsAggregator(
            gnews_api_key=self.config.news.gnews_api_key,
            newsapi_key=self.config.news.newsapi_key
        )
        
        self.chart_analyzer = ChartAnalyzer()
        self.strategy_manager = StrategyManager()
        self.risk_manager = RiskManager(RiskParameters(
            max_position_size_usd=self.config.risk.max_position_size,
            stop_loss_pct=self.config.risk.stop_loss_pct,
            take_profit_pct=self.config.risk.take_profit_pct,
            max_daily_loss_usd=self.config.risk.max_daily_loss,
            max_open_positions=self.config.risk.max_open_positions
        ))
        
        # Initialize AI agent if API key is configured
        if self.config.ai.openai_api_key:
            self.ai_agent = TradingAI(
                api_key=self.config.ai.openai_api_key,
                base_url=self.config.ai.openai_base_url,
                model=self.config.ai.model_name,
                temperature=self.config.ai.temperature
            )
        else:
            self.ai_agent = None
        
        self.backtest_engine = BacktestEngine(
            initial_capital=self.config.backtest.initial_capital,
            commission_rate=self.config.backtest.commission_rate,
            slippage_rate=self.config.backtest.slippage_rate
        )
        
        # Trading state
        self.is_running = False
        self.paper_trading = self.config.paper_trading
        self.tracked_symbols: List[str] = []
        self.active_strategy = "balanced"
        
        # Performance tracking
        self.trade_log: List[Dict] = []
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0
        }
    
    def add_symbol(self, symbol: str, exchange: str = 'binance'):
        """Add a symbol to track and trade."""
        self.tracked_symbols.append({
            'symbol': symbol,
            'exchange': exchange
        })
        print(f"Added {symbol} on {exchange} to tracking list")
    
    def set_strategy(self, strategy_name: str) -> bool:
        """Set the active trading strategy."""
        if strategy_name in self.strategy_manager.list_strategies():
            self.strategy_manager.set_active_strategy(strategy_name)
            self.active_strategy = strategy_name
            return True
        return False
    
    def analyze_symbol(self, symbol: str, exchange: str = 'binance') -> Dict:
        """Perform comprehensive analysis on a symbol."""
        # Get market data
        candles = self.exchange_manager.get_historical_data(
            symbol=symbol,
            interval='1h',
            limit=100,
            exchange=exchange
        )
        
        if not candles or len(candles) < 30:
            return {'error': 'Insufficient data'}
        
        # Get recent trades for whale detection
        trades = []
        try:
            if exchange.lower() == 'binance':
                trades = self.exchange_manager.binance.get_recent_trades(symbol, limit=100)
        except Exception as e:
            pass  # Whale data optional
        
        # Get order book
        order_book = {}
        try:
            if hasattr(self.exchange_manager.binance, 'get_order_book'):
                order_book = self.exchange_manager.binance.get_order_book(symbol)
        except:
            pass
        
        # Technical analysis
        technical_analysis = self.chart_analyzer.analyze(candles, trades, order_book)
        
        # News sentiment
        news_sentiment = self.news_aggregator.get_market_sentiment("all")
        
        # Extract signals from technical analysis
        signals = technical_analysis.get('signals', [])
        
        # Aggregate signals using strategy
        strategy = self.strategy_manager.get_active_strategy()
        aggregated = self.strategy_manager.aggregate_signals(signals, strategy)
        
        # Get AI recommendation if available
        ai_recommendation = None
        if self.ai_agent:
            ai_recommendation = self.ai_agent.analyze_market(
                symbol=symbol,
                technical_data=technical_analysis,
                news_sentiment=news_sentiment,
                whale_activity=technical_analysis.get('whale_activity', [])
            )
        
        return {
            'symbol': symbol,
            'exchange': exchange,
            'timestamp': datetime.now().isoformat(),
            'current_price': technical_analysis.get('current_price', 0),
            'technical_analysis': technical_analysis,
            'news_sentiment': news_sentiment,
            'aggregated_signal': aggregated,
            'ai_recommendation': ai_recommendation,
            'strategy': self.active_strategy
        }
    
    def execute_trade(self, symbol: str, side: str, quantity: float,
                     price: Optional[float] = None, exchange: str = 'binance') -> Dict:
        """Execute a trade (real or paper)."""
        
        # Check risk limits
        check_price = price or self.exchange_manager.get_price(symbol, exchange)
        risk_check = self.risk_manager.check_risk_limits(symbol, side, quantity, check_price)
        
        if not risk_check['approved']:
            return {
                'success': False,
                'reason': risk_check['reason'],
                'type': 'RISK_REJECTION'
            }
        
        if self.paper_trading:
            # Paper trade simulation
            result = self._execute_paper_trade(symbol, side, quantity, check_price)
        else:
            # Real trade execution
            result = self.exchange_manager.execute_trade(
                exchange=exchange,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_type='market' if not price else 'limit'
            )
        
        # Log trade
        if result.get('success', False):
            self.trade_log.append({
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': check_price,
                'paper_trade': self.paper_trading,
                'result': result
            })
            
            self.performance_metrics['total_trades'] += 1
        
        return result
    
    def _execute_paper_trade(self, symbol: str, side: str, 
                            quantity: float, price: float) -> Dict:
        """Simulate a paper trade."""
        # In a real implementation, this would track virtual positions
        return {
            'success': True,
            'type': 'PAPER_TRADE',
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'estimated_value': quantity * price,
            'message': 'Paper trade executed successfully'
        }
    
    def run_auto_trading_cycle(self):
        """Run one cycle of the auto-trading logic."""
        print(f"\n[{datetime.now()}] Running trading cycle...")
        
        for tracked in self.tracked_symbols:
            symbol = tracked['symbol']
            exchange = tracked['exchange']
            
            # Analyze
            analysis = self.analyze_symbol(symbol, exchange)
            
            if 'error' in analysis:
                continue
            
            # Get decision
            action = analysis['aggregated_signal'].get('action', 'HOLD')
            confidence = analysis['aggregated_signal'].get('confidence', 0)
            
            # Consider AI recommendation if available
            if analysis.get('ai_recommendation'):
                ai_rec = analysis['ai_recommendation'].get('recommendation', 'HOLD')
                ai_conf = analysis['ai_recommendation'].get('confidence', 0)
                
                # If AI strongly disagrees, be cautious
                if ai_rec != action and ai_conf > 0.8:
                    print(f"AI disagreement detected for {symbol}: Strategy={action}, AI={ai_rec}")
                    action = 'HOLD'  # Stay out when uncertain
            
            # Execute if signal is strong enough
            if action in ['BUY', 'SELL'] and confidence >= 0.6:
                current_price = analysis['current_price']
                
                # Calculate position size
                position_size = self.risk_manager.calculate_position_size(
                    method='percentage',
                    signal_strength=confidence
                )
                
                quantity = position_size / current_price
                
                print(f"Signal: {action} {symbol} | Confidence: {confidence*100:.1f}% | Qty: {quantity:.4f}")
                
                # Execute trade
                result = self.execute_trade(symbol, action, quantity, exchange=exchange)
                
                if result.get('success'):
                    print(f"✓ Trade executed: {action} {quantity:.4f} {symbol} @ ${current_price:.2f}")
                else:
                    print(f"✗ Trade rejected: {result.get('reason', 'Unknown')}")
    
    def start_auto_trading(self, interval_minutes: int = 15):
        """Start automated trading loop."""
        if self.is_running:
            print("Auto-trading already running")
            return
        
        self.is_running = True
        print(f"Starting auto-trading (Paper Mode: {self.paper_trading})")
        print(f"Tracking {len(self.tracked_symbols)} symbols")
        print(f"Using strategy: {self.active_strategy}")
        
        def trading_loop():
            while self.is_running:
                try:
                    self.run_auto_trading_cycle()
                    time.sleep(interval_minutes * 60)
                except KeyboardInterrupt:
                    print("\nStopping auto-trading...")
                    self.is_running = False
                except Exception as e:
                    print(f"Error in trading cycle: {e}")
                    time.sleep(60)  # Wait before retry
        
        # Run in background thread
        thread = threading.Thread(target=trading_loop, daemon=True)
        thread.start()
        
        return thread
    
    def stop_auto_trading(self):
        """Stop automated trading."""
        self.is_running = False
        print("Auto-trading stopped")
    
    def get_performance_report(self) -> Dict:
        """Get current performance metrics."""
        report = {
            'mode': 'PAPER' if self.paper_trading else 'LIVE',
            'strategy': self.active_strategy,
            'tracked_symbols': len(self.tracked_symbols),
            'metrics': self.performance_metrics,
            'risk_status': self.risk_manager.get_risk_report(),
            'recent_trades': self.trade_log[-10:]  # Last 10 trades
        }
        
        if self.performance_metrics['total_trades'] > 0:
            report['win_rate'] = (
                self.performance_metrics['winning_trades'] / 
                self.performance_metrics['total_trades'] * 100
            )
        
        return report
    
    def toggle_paper_trading(self):
        """Toggle between paper and live trading mode."""
        self.paper_trading = not self.paper_trading
        mode = "PAPER" if self.paper_trading else "LIVE"
        print(f"Trading mode switched to: {mode}")
        return self.paper_trading


# Example usage
if __name__ == "__main__":
    # Create bot instance
    bot = TradingBot()
    
    # Add symbols to track
    bot.add_symbol("BTCUSDT", "binance")
    bot.add_symbol("ETHUSDT", "binance")
    
    # Set strategy
    bot.set_strategy("balanced")
    
    # Get analysis
    analysis = bot.analyze_symbol("BTCUSDT")
    print(f"BTC Analysis: {analysis['aggregated_signal']}")
    
    # Get performance
    report = bot.get_performance_report()
    print(f"\nPerformance Report: {report}")
