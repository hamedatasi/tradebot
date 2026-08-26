"""
AI Agent for trading recommendations using OpenAI-compatible endpoints.
Analyzes market data and provides buy/sell suggestions with reasoning.
"""
from typing import Dict, List, Optional
import json
import requests


class TradingAI:
    """
    AI agent that connects to OpenAI-compatible endpoints to analyze
    trading data and provide recommendations.
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-3.5-turbo", temperature: float = 0.7):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        
        # System prompt for trading analysis
        self.system_prompt = """You are an expert cryptocurrency trading analyst. 
Your role is to analyze market data and provide clear, actionable trading recommendations.

Always structure your response in the following JSON format:
{
    "recommendation": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your analysis",
    "entry_price": suggested_entry_price_or_null,
    "stop_loss": stop_loss_price_or_null,
    "take_profit_1": first_target_or_null,
    "take_profit_2": second_target_or_null,
    "risk_reward_ratio": calculated_ratio_or_null,
    "time_horizon": "short_term" | "medium_term" | "long_term",
    "key_factors": ["factor1", "factor2", ...],
    "warnings": ["any_risk_warnings"]
}

Consider technical indicators, price action, volume, whale activity, and market sentiment.
Be conservative in uncertain conditions and more confident when multiple signals align."""
    
    def analyze_market(self, symbol: str, technical_data: Dict, 
                      news_sentiment: Dict = None, whale_activity: List = None,
                      custom_context: str = None) -> Dict:
        """
        Analyze market data and get AI recommendation.
        
        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            technical_data: Technical analysis results
            news_sentiment: News sentiment data
            whale_activity: Recent whale trades
            custom_context: Additional context or user notes
        
        Returns:
            AI recommendation as dictionary
        """
        # Build comprehensive prompt
        user_prompt = self._build_analysis_prompt(
            symbol=symbol,
            technical=technical_data,
            news=news_sentiment,
            whales=whale_activity,
            custom=custom_context
        )
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self._call_llm(messages)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                content = response['choices'][0]['message']['content']
                
                # Try to parse JSON from response
                recommendation = self._parse_response(content)
                
                if recommendation:
                    return {
                        'success': True,
                        'symbol': symbol,
                        'timestamp': technical_data.get('timestamp', 0),
                        **recommendation
                    }
            
            return {
                'success': False,
                'error': 'Failed to get valid AI response',
                'recommendation': 'HOLD',
                'confidence': 0.0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'recommendation': 'HOLD',
                'confidence': 0.0
            }
    
    def _build_analysis_prompt(self, symbol: str, technical: Dict, 
                               news: Dict = None, whales: List = None,
                               custom: str = None) -> str:
        """Build comprehensive analysis prompt for the AI."""
        prompt_parts = [f"Analyze {symbol} based on the following data:\n"]
        
        # Technical Analysis
        prompt_parts.append("TECHNICAL ANALYSIS:")
        if 'indicators' in technical:
            indicators = technical['indicators']
            
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                rsi_status = "OVERSOLD" if rsi < 30 else "OVERBOUGHT" if rsi > 70 else "NEUTRAL"
                prompt_parts.append(f"- RSI: {rsi:.2f} ({rsi_status})")
            
            if 'macd' in indicators:
                macd = indicators['macd']
                signal = indicators.get('signal', {})
                histogram = indicators.get('histogram', 0)
                trend = "BULLISH" if histogram > 0 else "BEARISH" if histogram < 0 else "NEUTRAL"
                prompt_parts.append(f"- MACD: {macd:.4f}, Signal: {signal:.4f}, Histogram: {histogram:.4f} ({trend})")
            
            if 'bollinger' in indicators:
                bb = indicators['bollinger']
                position = bb.get('position', 0.5)
                prompt_parts.append(f"- Bollinger Bands Position: {position:.2%} (0=lower band, 1=upper band)")
            
            if 'atr' in indicators:
                prompt_parts.append(f"- ATR (Volatility): {indicators['atr']:.4f}")
            
            if 'vwap' in indicators:
                current_price = technical.get('current_price', 0)
                vwap = indicators['vwap']
                position_vs_vwap = "ABOVE" if current_price > vwap else "BELOW"
                prompt_parts.append(f"- VWAP: {vwap:.2f}, Price is {position_vs_vwap} VWAP")
        
        # Patterns
        if 'patterns' in technical and technical['patterns']:
            prompt_parts.append("\nDETECTED PATTERNS:")
            for pattern in technical['patterns']:
                prompt_parts.append(f"- {pattern.get('pattern', 'Unknown')}: {pattern.get('signal', '')} signal with {pattern.get('confidence', 0)*100:.0f}% confidence")
        
        # Whale Activity
        if whales and len(whales) > 0:
            prompt_parts.append("\nWHALE ACTIVITY:")
            recent_whales = whales[-5:] if len(whales) > 5 else whales
            buy_count = sum(1 for w in recent_whales if w.get('is_buy', False))
            sell_count = len(recent_whales) - buy_count
            prompt_parts.append(f"- Recent large trades: {len(recent_whales)}")
            prompt_parts.append(f"- Buy pressure: {buy_count}, Sell pressure: {sell_count}")
            
            avg_whale_score = sum(w.get('whale_score', 0) for w in recent_whales) / len(recent_whales)
            prompt_parts.append(f"- Average whale score: {avg_whale_score:.2f}")
        
        # News Sentiment
        if news:
            prompt_parts.append("\nNEWS SENTIMENT:")
            sentiment_score = news.get('sentiment_score', 0)
            sentiment_label = news.get('sentiment_label', 'neutral')
            prompt_parts.append(f"- Overall Sentiment: {sentiment_label} ({sentiment_score:.2f})")
            
            if 'recent_articles' in news and news['recent_articles']:
                prompt_parts.append("- Recent Headlines:")
                for article in news['recent_articles'][:3]:
                    title = article.get('title', '')[:80]
                    sent = article.get('sentiment', 0)
                    prompt_parts.append(f"  * {title} (sentiment: {sent:.2f})")
        
        # Current Price
        if 'current_price' in technical:
            prompt_parts.append(f"\nCURRENT PRICE: ${technical['current_price']:.2f}")
        
        # Custom Context
        if custom:
            prompt_parts.append(f"\nADDITIONAL CONTEXT:\n{custom}")
        
        prompt_parts.append("\n\nProvide your trading recommendation in the specified JSON format.")
        
        return "\n".join(prompt_parts)
    
    def _call_llm(self, messages: List[Dict]) -> Dict:
        """Call the LLM API."""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': 1000
        }
        
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def _parse_response(self, content: str) -> Optional[Dict]:
        """Parse AI response to extract JSON recommendation."""
        # Try to find JSON in the response
        try:
            # Direct JSON parse
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object anywhere in text
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        
        # Fallback: create structured response from text
        return {
            'recommendation': 'HOLD',
            'confidence': 0.5,
            'reasoning': content[:500] if len(content) > 500 else content,
            'key_factors': ['AI analysis provided in text format'],
            'warnings': ['Could not parse structured response']
        }
    
    def compare_strategies(self, symbol: str, strategy_signals: Dict,
                          ai_recommendation: Dict) -> Dict:
        """
        Compare AI recommendation with strategy-generated signals.
        """
        comparison = {
            'symbol': symbol,
            'ai_recommendation': ai_recommendation.get('recommendation', 'HOLD'),
            'ai_confidence': ai_recommendation.get('confidence', 0),
            'strategy_signals': {},
            'agreement': False,
            'conflict_reason': None
        }
        
        # Analyze strategy signals
        buy_count = sum(1 for s in strategy_signals if s.action == 'BUY')
        sell_count = sum(1 for s in strategy_signals if s.action == 'SELL')
        
        if buy_count > sell_count:
            strategy_rec = 'BUY'
        elif sell_count > buy_count:
            strategy_rec = 'SELL'
        else:
            strategy_rec = 'HOLD'
        
        comparison['strategy_signals'] = {
            'buy_signals': buy_count,
            'sell_signals': sell_count,
            'total_signals': len(strategy_signals),
            'recommendation': strategy_rec
        }
        
        # Check agreement
        if ai_recommendation.get('recommendation') == strategy_rec:
            comparison['agreement'] = True
            comparison['combined_confidence'] = (
                ai_recommendation.get('confidence', 0) + 
                (max(buy_count, sell_count) / max(len(strategy_signals), 1))
            ) / 2
        else:
            comparison['conflict_reason'] = f"AI suggests {ai_recommendation.get('recommendation')} while strategy indicates {strategy_rec}"
        
        return comparison
    
    def explain_decision(self, recommendation: Dict, market_context: Dict) -> str:
        """Generate human-readable explanation of the AI's decision."""
        exp_parts = []
        
        exp_parts.append(f"**Recommendation: {recommendation.get('recommendation', 'HOLD')}**")
        exp_parts.append(f"Confidence: {recommendation.get('confidence', 0)*100:.1f}%\n")
        
        reasoning = recommendation.get('reasoning', 'No reasoning provided')
        exp_parts.append(f"Analysis: {reasoning}\n")
        
        if 'key_factors' in recommendation:
            exp_parts.append("Key Factors:")
            for factor in recommendation['key_factors']:
                exp_parts.append(f"• {factor}")
        
        if 'entry_price' in recommendation and recommendation['entry_price']:
            exp_parts.append(f"\nSuggested Entry: ${recommendation['entry_price']:.2f}")
        
        if 'stop_loss' in recommendation and recommendation['stop_loss']:
            exp_parts.append(f"Stop Loss: ${recommendation['stop_loss']:.2f}")
        
        if 'take_profit_1' in recommendation and recommendation['take_profit_1']:
            exp_parts.append(f"Take Profit 1: ${recommendation['take_profit_1']:.2f}")
        
        if 'take_profit_2' in recommendation and recommendation['take_profit_2']:
            exp_parts.append(f"Take Profit 2: ${recommendation['take_profit_2']:.2f}")
        
        if 'risk_reward_ratio' in recommendation and recommendation['risk_reward_ratio']:
            exp_parts.append(f"Risk/Reward Ratio: 1:{recommendation['risk_reward_ratio']:.2f}")
        
        if 'warnings' in recommendation and recommendation['warnings']:
            exp_parts.append("\n⚠️ Warnings:")
            for warning in recommendation['warnings']:
                exp_parts.append(f"• {warning}")
        
        return "\n".join(exp_parts)


# Simple test without API key
if __name__ == "__main__":
    print("TradingAI module loaded successfully")
    print("Configure with your OpenAI-compatible API endpoint to use")
