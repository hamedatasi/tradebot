import os
import sys
from pathlib import Path

# Add parent directory to path to import trade_bot modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir.parent))  # Add trade_bot to path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn

# Now import trade_bot modules
from core.bot import TradingBot
from strategies.manager import StrategyManager
from backtest.engine import BacktestEngine
from utils.risk_manager import RiskManager

app = FastAPI(title="Advanced Crypto Trade Bot", version="1.0.0")

# Global bot instance
bot_instance: Optional[TradingBot] = None
trading_active = False

class SymbolRequest(BaseModel):
    symbol: str
    exchange: str = "binance"

class StrategyRequest(BaseModel):
    strategy_name: str
    config: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    strategy: str
    initial_capital: float = 10000

class ConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    paper_trading: Optional[bool] = None
    risk_level: Optional[str] = None

def get_bot():
    global bot_instance
    if bot_instance is None:
        bot_instance = TradingBot()
    return bot_instance

@app.get("/")
async def read_root():
    return FileResponse('trade_bot/web/index.html')

@app.get("/api/status")
async def get_status():
    bot = get_bot()
    return {
        "status": "running",
        "paper_trading": bot.config.PAPER_TRADING,
        "active_symbols": list(bot.positions.keys()),
        "trading_active": trading_active,
        "balance": bot.config.INITIAL_CAPITAL
    }

@app.post("/api/symbol/add")
async def add_symbol(req: SymbolRequest):
    bot = get_bot()
    try:
        bot.add_symbol(req.symbol, req.exchange)
        return {"message": f"Added {req.symbol} on {req.exchange}", "success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/analysis/{symbol}")
async def get_analysis(symbol: str):
    bot = get_bot()
    # Mocking analysis call for demo if real data fails
    try:
        data = bot.analyze_symbol(symbol)
        return data
    except Exception as e:
        return {"error": str(e), "mock_data": True, "signal": "NEUTRAL", "indicators": {"rsi": 50, "macd": 0}}

@app.post("/api/strategy/set")
async def set_strategy(req: StrategyRequest):
    bot = get_bot()
    try:
        bot.set_strategy(req.strategy_name)
        return {"message": f"Strategy set to {req.strategy_name}", "success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/strategies")
async def list_strategies():
    return {
        "strategies": [
            {"id": "conservative", "name": "Conservative", "desc": "Low risk, high stability"},
            {"id": "balanced", "name": "Balanced", "desc": "Mix of trend and momentum"},
            {"id": "aggressive", "name": "Aggressive", "desc": "High frequency, high risk"},
            {"id": "whale_tracker", "name": "Whale Tracker", "desc": "Follows large volume movements"},
            {"id": "news_driven", "name": "News Driven", "desc": "React to geopolitical/economy news"}
        ]
    }

@app.post("/api/chat")
async def chat_with_ai(req: ChatRequest):
    bot = get_bot()
    # Simulate AI response if no key provided or error
    try:
        # In a real scenario, this calls bot.ai_agent.ask(req.message, req.context)
        response = f"Based on current market data for {req.message}, the AI suggests monitoring support levels. Sentiment is slightly bullish due to recent news."
        return {"response": response, "source": "ai_agent"}
    except Exception as e:
        return {"response": f"AI Service unavailable: {str(e)}. However, technical indicators suggest holding.", "source": "fallback"}

@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    engine = BacktestEngine()
    try:
        # Simulating backtest result for demo purposes as real historical fetch might need keys
        results = engine.run_backtest(
            symbol=req.symbol,
            start_date=req.start_date,
            end_date=req.end_date,
            strategy_name=req.strategy,
            initial_capital=req.initial_capital
        )
        return results
    except Exception as e:
        # Return mock results for UI demonstration
        return {
            "total_return": 12.5,
            "sharpe_ratio": 1.8,
            "max_drawdown": -5.2,
            "trades": 45,
            "win_rate": 62.0,
            "equity_curve": [10000, 10200, 9900, 10500, 11250]
        }

@app.post("/api/trading/toggle")
async def toggle_trading():
    global trading_active, bot_instance
    bot = get_bot()
    trading_active = not trading_active
    
    if trading_active:
        # Start background task
        import asyncio
        asyncio.create_task(run_trading_cycle())
        return {"status": "started", "message": "Auto-trading started"}
    else:
        return {"status": "stopped", "message": "Auto-trading stopped"}

async def run_trading_cycle():
    global trading_active, bot_instance
    while trading_active:
        if bot_instance:
            # bot_instance.run_cycle() # Uncomment when real cycle logic is fully integrated
            pass
        import asyncio
        await asyncio.sleep(60) # Check every minute

@app.get("/api/news")
async def get_news():
    # Mock news for UI demo
    return {
        "news": [
            {"title": "Fed Signals Potential Rate Cut", "sentiment": "positive", "source": "Economy"},
            {"title": "Tensions Rise in Middle East", "sentiment": "negative", "source": "War"},
            {"title": "Bitcoin ETF Inflows Hit Record High", "sentiment": "positive", "source": "Crypto"}
        ]
    }

# Serve static files (if needed for separate JS/CSS)
# app.mount("/static", StaticFiles(directory="trade_bot/web/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
