"""
News aggregator for economic and war-related news.
Uses free APIs to fetch and analyze news sentiment.
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json


class NewsAggregator:
    """Aggregates news from multiple free sources."""
    
    def __init__(self, gnews_api_key: str = "", newsapi_key: str = ""):
        self.gnews_api_key = gnews_api_key
        self.newsapi_key = newsapi_key
        self.sources = []
        
        if gnews_api_key:
            self.sources.append('gnews')
        if newsapi_key:
            self.sources.append('newsapi')
    
    def get_usa_economy_news(self, limit: int = 10) -> List[Dict]:
        """Fetch latest USA economy news."""
        articles = []
        
        # Try GNews API (free tier: 100 requests/day)
        if 'gnews' in self.sources:
            articles.extend(self._fetch_gnews(
                query="USA economy OR Federal Reserve OR inflation OR interest rates OR GDP",
                limit=limit
            ))
        
        # Try NewsAPI (free tier: 100 requests/day)
        if 'newsapi' in self.sources:
            articles.extend(self._fetch_newsapi(
                query="economy inflation federal reserve interest rates",
                category="business",
                limit=limit
            ))
        
        # Fallback to RSS feeds if no API keys
        if not self.sources:
            articles.extend(self._fetch_crypto_panic_news())
        
        return articles[:limit]
    
    def get_war_news(self, limit: int = 10) -> List[Dict]:
        """Fetch latest war/geopolitical news."""
        articles = []
        
        if 'gnews' in self.sources:
            articles.extend(self._fetch_gnews(
                query="war OR conflict OR geopolitics OR military OR tension",
                limit=limit
            ))
        
        if 'newsapi' in self.sources:
            articles.extend(self._fetch_newsapi(
                query="war conflict geopolitics military",
                category="general",
                limit=limit
            ))
        
        if not self.sources:
            articles.extend(self._fetch_reuters_world_news())
        
        return articles[:limit]
    
    def _fetch_gnews(self, query: str, limit: int = 10) -> List[Dict]:
        """Fetch news from GNews API."""
        url = "https://gnews.io/api/v4/search"
        params = {
            'q': query,
            'token': self.gnews_api_key,
            'lang': 'en',
            'country': 'us',
            'max': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            articles = []
            for item in data.get('articles', []):
                articles.append({
                    'title': item.get('title', ''),
                    'description': item.get('description', ''),
                    'url': item.get('url', ''),
                    'source': item.get('source', {}).get('name', 'GNews'),
                    'published_at': item.get('publishedAt', ''),
                    'sentiment': self._analyze_sentiment_simple(item.get('title', '') + ' ' + item.get('description', ''))
                })
            return articles
        except Exception as e:
            print(f"GNews API error: {e}")
            return []
    
    def _fetch_newsapi(self, query: str, category: str = "general", limit: int = 10) -> List[Dict]:
        """Fetch news from NewsAPI."""
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'category': category,
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': limit,
            'apiKey': self.newsapi_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') != 'ok':
                return []
            
            articles = []
            for item in data.get('articles', []):
                articles.append({
                    'title': item.get('title', ''),
                    'description': item.get('description', ''),
                    'url': item.get('url', ''),
                    'source': item.get('source', {}).get('name', 'NewsAPI'),
                    'published_at': item.get('publishedAt', ''),
                    'sentiment': self._analyze_sentiment_simple(item.get('title', '') + ' ' + item.get('description', ''))
                })
            return articles
        except Exception as e:
            print(f"NewsAPI error: {e}")
            return []
    
    def _fetch_crypto_panic_news(self, limit: int = 10) -> List[Dict]:
        """Fetch crypto news from CryptoPanic (free, no API key needed for basic)."""
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {'public': 'true', 'limit': limit}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            articles = []
            for item in data.get('results', [])[:limit]:
                articles.append({
                    'title': item.get('title', ''),
                    'description': item.get('body', ''),
                    'url': item.get('url', ''),
                    'source': 'CryptoPanic',
                    'published_at': item.get('published_at', ''),
                    'sentiment': self._analyze_sentiment_simple(item.get('title', ''))
                })
            return articles
        except Exception as e:
            print(f"CryptoPanic error: {e}")
            return []
    
    def _fetch_reuters_world_news(self, limit: int = 10) -> List[Dict]:
        """Fallback: Fetch from Reuters RSS or similar free source."""
        # This is a placeholder - in production, you'd parse RSS feeds
        return [{
            'title': 'Global Markets Update',
            'description': 'Check financial news sources for latest updates',
            'url': 'https://reuters.com',
            'source': 'Reuters',
            'published_at': datetime.now().isoformat(),
            'sentiment': 0.0
        }]
    
    def _analyze_sentiment_simple(self, text: str) -> float:
        """
        Simple sentiment analysis without external APIs.
        Returns score between -1 (negative) and 1 (positive).
        """
        text_lower = text.lower()
        
        positive_words = [
            'growth', 'gain', 'rise', 'increase', 'bullish', 'positive',
            'strong', 'profit', 'success', 'optimistic', 'rally', 'boom',
            'record', 'high', 'surge', 'jump', 'soar'
        ]
        
        negative_words = [
            'crash', 'fall', 'drop', 'decline', 'bearish', 'negative',
            'weak', 'loss', 'failure', 'pessimistic', 'slump', 'crisis',
            'low', 'plunge', 'tumble', 'collapse', 'war', 'conflict',
            'tension', 'sanction', 'threat', 'fear', 'panic'
        ]
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    def get_market_sentiment(self, news_type: str = "all") -> Dict:
        """
        Calculate overall market sentiment from news.
        Returns sentiment score and summary.
        """
        if news_type == "economy":
            articles = self.get_usa_economy_news(limit=20)
        elif news_type == "war":
            articles = self.get_war_news(limit=20)
        else:
            economy = self.get_usa_economy_news(limit=10)
            war = self.get_war_news(limit=10)
            articles = economy + war
        
        if not articles:
            return {
                'sentiment_score': 0.0,
                'sentiment_label': 'neutral',
                'article_count': 0,
                'summary': 'No news available'
            }
        
        avg_sentiment = sum(article['sentiment'] for article in articles) / len(articles)
        
        if avg_sentiment > 0.3:
            label = 'bullish'
        elif avg_sentiment < -0.3:
            label = 'bearish'
        else:
            label = 'neutral'
        
        return {
            'sentiment_score': round(avg_sentiment, 3),
            'sentiment_label': label,
            'article_count': len(articles),
            'recent_articles': articles[:5],
            'summary': f"Market sentiment is {label} based on {len(articles)} articles"
        }
    
    def get_impact_events(self, hours: int = 24) -> List[Dict]:
        """Identify high-impact news events that could move markets."""
        all_news = self.get_usa_economy_news(limit=50) + self.get_war_news(limit=50)
        
        impact_events = []
        for article in all_news:
            # Check for high-impact keywords
            high_impact_keywords = [
                'federal reserve', 'interest rate', 'inflation data',
                'gdp report', 'unemployment', 'war', 'sanction',
                'emergency', 'crisis', 'breaking'
            ]
            
            title_lower = article['title'].lower()
            desc_lower = (article['description'] or '').lower()
            
            impact_score = sum(1 for keyword in high_impact_keywords 
                             if keyword in title_lower or keyword in desc_lower)
            
            if impact_score >= 2 or abs(article['sentiment']) > 0.5:
                impact_events.append({
                    **article,
                    'impact_score': impact_score + abs(article['sentiment']),
                    'potential_market_impact': 'high' if impact_score >= 3 else 'medium'
                })
        
        # Sort by impact score
        impact_events.sort(key=lambda x: x['impact_score'], reverse=True)
        return impact_events[:10]


# Example usage without API keys (uses fallback methods)
if __name__ == "__main__":
    aggregator = NewsAggregator()
    print("Economy News Sentiment:", aggregator.get_market_sentiment("economy"))
    print("War News Sentiment:", aggregator.get_market_sentiment("war"))
