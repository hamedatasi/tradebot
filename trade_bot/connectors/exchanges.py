"""
Exchange connectors for Nobitex and Binance.
Handles API connections, order execution, and data retrieval.
"""
import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import requests
from datetime import datetime


class BaseExchange(ABC):
    """Abstract base class for exchange connectors."""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.base_url = self.get_base_url()
        self.session = requests.Session()
        
    @abstractmethod
    def get_base_url(self) -> str:
        """Get the base URL for the exchange API."""
        pass
    
    @abstractmethod
    def _sign_request(self, params: dict) -> dict:
        """Sign the request with API credentials."""
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        """Get current ticker data for a symbol."""
        pass
    
    @abstractmethod
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List:
        """Get candlestick/kline data."""
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict:
        """Get account balance."""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: float, 
                   price: Optional[float] = None, order_type: str = "market") -> Dict:
        """Place a trading order."""
        pass
    
    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order."""
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List:
        """Get open orders."""
        pass
    
    def _make_request(self, method: str, endpoint: str, params: dict = None, 
                     signed: bool = False) -> Dict:
        """Make HTTP request to exchange API."""
        url = f"{self.base_url}{endpoint}"
        
        if signed:
            params = self._sign_request(params or {})
        
        try:
            response = self.session.request(method, url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {"error": str(e)}


class BinanceConnector(BaseExchange):
    """Binance exchange connector."""
    
    def get_base_url(self) -> str:
        if self.sandbox:
            return "https://testnet.binance.vision"
        return "https://api.binance.com"
    
    def _sign_request(self, params: dict) -> dict:
        """Sign request with HMAC SHA256."""
        params['timestamp'] = int(time.time() * 1000)
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature
        return params
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker price change statistics."""
        params = {'symbol': symbol.upper()}
        return self._make_request('GET', '/api/v3/ticker/24hr', params)
    
    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> List:
        """Get candlestick data."""
        params = {
            'symbol': symbol.upper(),
            'interval': interval,
            'limit': limit
        }
        data = self._make_request('GET', '/api/v3/klines', params)
        # Convert to OHLCV format
        if isinstance(data, list):
            return [{
                'timestamp': candle[0],
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            } for candle in data]
        return data
    
    def get_balance(self) -> Dict:
        """Get account balance."""
        params = {}
        return self._make_request('GET', '/api/v3/account', params, signed=True)
    
    def place_order(self, symbol: str, side: str, quantity: float,
                   price: Optional[float] = None, order_type: str = "market") -> Dict:
        """Place order on Binance."""
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity,
            'recvWindow': 5000
        }
        
        if order_type.lower() == "limit" and price:
            params['price'] = price
            params['timeInForce'] = 'GTC'
        
        return self._make_request('POST', '/api/v3/order', params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel order on Binance."""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        return self._make_request('DELETE', '/api/v3/order', params, signed=True)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List:
        """Get open orders."""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
        return self._make_request('GET', '/api/v3/openOrders', params, signed=True)
    
    def get_recent_trades(self, symbol: str, limit: int = 500) -> List:
        """Get recent trades to analyze whale activity."""
        params = {
            'symbol': symbol.upper(),
            'limit': limit
        }
        return self._make_request('GET', '/api/v3/trades', params)


class NobitexConnector(BaseExchange):
    """Nobitex exchange connector (Iranian exchange)."""
    
    def get_base_url(self) -> str:
        if self.sandbox:
            return "https://api.nobitex.ir"  # Use main API, check for testnet
        return "https://api.nobitex.ir"
    
    def _sign_request(self, params: dict) -> dict:
        """Sign request for Nobitex API."""
        # Nobitex uses token-based authentication
        params['token'] = self.api_key
        return params
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get ticker data from Nobitex."""
        # Nobitex uses src-dest format (e.g., btc-usdt)
        endpoint = f"/market/stats?src={symbol.split('-')[0]}&dest={symbol.split('-')[1]}"
        return self._make_request('GET', endpoint, {}, signed=False)
    
    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> List:
        """Get candlestick data from Nobitex."""
        src = symbol.split('-')[0]
        dest = symbol.split('-')[1]
        endpoint = f"/market/chart/{src}-{dest}"
        params = {
            'interval': interval,
            'limit': limit
        }
        data = self._make_request('GET', endpoint, params, signed=False)
        
        if 'stats' in data:
            # Convert Nobitex format to OHLCV
            stats = data['stats']
            candles = []
            for timestamp, candle_data in stats.items():
                candles.append({
                    'timestamp': int(timestamp) * 1000,
                    'open': float(candle_data.get('first', 0)),
                    'high': float(candle_data.get('max', 0)),
                    'low': float(candle_data.get('min', 0)),
                    'close': float(candle_data.get('last', 0)),
                    'volume': float(candle_data.get('volume', 0))
                })
            return sorted(candles, key=lambda x: x['timestamp'])
        return []
    
    def get_balance(self) -> Dict:
        """Get account balance from Nobitex."""
        return self._make_request('POST', '/users/wallets/balance', {}, signed=True)
    
    def place_order(self, symbol: str, side: str, quantity: float,
                   price: Optional[float] = None, order_type: str = "market") -> Dict:
        """Place order on Nobitex."""
        src = symbol.split('-')[0]
        dest = symbol.split('-')[1]
        
        params = {
            'src': src,
            'dest': dest,
            'amount': quantity,
            'type': 'sell' if side.upper() == 'SELL' else 'buy'
        }
        
        if order_type.lower() == "limit" and price:
            params['price'] = price
        
        return self._make_request('POST', '/market/orders/create', params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel order on Nobitex."""
        params = {'id': order_id}
        return self._make_request('POST', '/market/orders/cancel', params, signed=True)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List:
        """Get open orders from Nobitex."""
        return self._make_request('POST', '/market/orders/open', {}, signed=True)
    
    def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        """Get order book for whale analysis."""
        src = symbol.split('-')[0]
        dest = symbol.split('-')[1]
        endpoint = f"/market/orderbook/{src}-{dest}"
        params = {'depth': depth}
        return self._make_request('GET', endpoint, params, signed=False)


class ExchangeManager:
    """Manages multiple exchange connections."""
    
    def __init__(self, nobitex_config: dict, binance_config: dict):
        self.nobitex = NobitexConnector(
            nobitex_config.get('api_key', ''),
            nobitex_config.get('api_secret', ''),
            nobitex_config.get('sandbox', True)
        )
        self.binance = BinanceConnector(
            binance_config.get('api_key', ''),
            binance_config.get('api_secret', ''),
            binance_config.get('sandbox', True)
        )
        self.active_exchanges = {}
    
    def get_exchange(self, name: str) -> BaseExchange:
        """Get exchange connector by name."""
        if name.lower() == 'nobitex':
            return self.nobitex
        elif name.lower() == 'binance':
            return self.binance
        raise ValueError(f"Unknown exchange: {name}")
    
    def get_price(self, symbol: str, exchange: str = 'binance') -> float:
        """Get current price from specified exchange."""
        exch = self.get_exchange(exchange)
        ticker = exch.get_ticker(symbol)
        
        if exchange.lower() == 'binance':
            return float(ticker.get('lastPrice', 0))
        elif exchange.lower() == 'nobitex':
            stats = ticker.get('stats', {})
            latest = stats.get(str(int(time.time())), {})
            return float(latest.get('last', 0))
        return 0.0
    
    def get_historical_data(self, symbol: str, interval: str = "1h", 
                           limit: int = 100, exchange: str = 'binance') -> List:
        """Get historical candlestick data."""
        exch = self.get_exchange(exchange)
        return exch.get_klines(symbol, interval, limit)
    
    def execute_trade(self, exchange: str, symbol: str, side: str, 
                     quantity: float, price: Optional[float] = None,
                     order_type: str = "market") -> Dict:
        """Execute trade on specified exchange."""
        exch = self.get_exchange(exchange)
        return exch.place_order(symbol, side, quantity, price, order_type)
