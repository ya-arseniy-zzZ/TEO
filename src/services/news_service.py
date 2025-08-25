"""
News service module for Teo bot
Handles NEWS API integration for Russian news
"""
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Setup logging
logger = logging.getLogger(__name__)

# API Configuration
NEWS_API_KEY = "fd239a6808e346eeaa5e59daac54cafc"
NEWS_API_BASE_URL = "https://newsapi.org/v2/everything"
REQUEST_TIMEOUT = 10

# News categories and their API queries
NEWS_CATEGORIES = {
    "latest": {
        "name": "Последние новости",
        "emoji": "📰",
        "url": f"{NEWS_API_BASE_URL}?language=ru&sortBy=publishedAt&pageSize=15&domains=rbc.ru,kommersant.ru,vedomosti.ru,interfax.ru,forbes.ru,tass.ru,lenta.ru&apiKey={NEWS_API_KEY}"
    },
    "popular": {
        "name": "Главные новости",
        "emoji": "🔥",
        "url": f"{NEWS_API_BASE_URL}?language=ru&sortBy=popularity&pageSize=15&searchIn=title,description&q=новости%20OR%20главное%20OR%20итоги&domains=rbc.ru,kommersant.ru,vedomosti.ru,interfax.ru,forbes.ru,tass.ru,lenta.ru&apiKey={NEWS_API_KEY}"
    },
    "sports": {
        "name": "Спорт",
        "emoji": "⚽",
        "url": f"{NEWS_API_BASE_URL}?language=ru&sortBy=publishedAt&pageSize=12&searchIn=title,description&q=спорт%20OR%20футбол%20OR%20хоккей%20OR%20теннис&domains=rbc.ru,lenta.ru,tass.ru&apiKey={NEWS_API_KEY}"
    },
    "economy": {
        "name": "Экономика и бизнес",
        "emoji": "💰",
        "url": f"{NEWS_API_BASE_URL}?language=ru&sortBy=publishedAt&pageSize=12&searchIn=title,description&q=экономика%20OR%20бизнес%20OR%20рынок%20OR%20ЦБ&domains=rbc.ru,kommersant.ru,vedomosti.ru,interfax.ru,forbes.ru&apiKey={NEWS_API_KEY}"
    },
    "technology": {
        "name": "Технологии и наука",
        "emoji": "🤖",
        "url": f"{NEWS_API_BASE_URL}?language=ru&sortBy=publishedAt&pageSize=12&searchIn=title,description&q=AI%20OR%20искусственный%20интеллект%20OR%20технологии%20OR%20наука%20OR%20IT&domains=rbc.ru,kommersant.ru,vedomosti.ru,lenta.ru&apiKey={NEWS_API_KEY}"
    }
}


class NewsService:
    """Handles news fetching and formatting"""
    
    def __init__(self):
        self.api_key = NEWS_API_KEY
        self.base_url = NEWS_API_BASE_URL
    
    def get_news(self, category: str = "latest", user_timezone: str = "UTC") -> Optional[Dict]:
        """
        Get news for a specific category
        
        Args:
            category: News category (latest, popular, sports, economy, technology)
            user_timezone: User's timezone for time formatting
            
        Returns:
            Dictionary with news data or None if error
        """
        if category not in NEWS_CATEGORIES:
            logger.error(f"Invalid news category: {category}")
            return None
        
        try:
            url = NEWS_CATEGORIES[category]["url"]
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"News API error: {data.get('message', 'Unknown error')}")
                return None
            
            return self._format_news_data(data, category, user_timezone)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news for category {category}: {e}")
            return None
        except KeyError as e:
            logger.error(f"Error parsing news data for category {category}: {e}")
            return None
    
    def _format_news_data(self, data: Dict, category: str, user_timezone: str = "UTC") -> Dict:
        """
        Format news data for display
        
        Args:
            data: Raw news API response
            category: News category
            user_timezone: User's timezone for time formatting
            
        Returns:
            Formatted news data
        """
        articles = data.get('articles', [])
        formatted_articles = []
        
        for article in articles:
            # Extract and format article data
            title = article.get('title', '').strip()
            description = article.get('description', '').strip()
            url = article.get('url', '')
            source = article.get('source', {}).get('name', '')
            published_at = article.get('publishedAt', '')
            image_url = article.get('urlToImage', '')  # Get image URL from API
            
            # Skip articles without title or URL
            if not title or not url:
                continue
            
            # Format publication time with user timezone
            try:
                import pytz
                pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                # Convert to user timezone
                user_tz = pytz.timezone(user_timezone)
                local_time = pub_time.astimezone(user_tz)
                
                # Format time based on category
                if category == "latest":
                    # For main news - show time only
                    time_str = local_time.strftime('%H:%M')
                else:
                    # For other categories - show date only
                    time_str = local_time.strftime('%m/%d/%Y')
                
                # Debug logging
                logger.info(f"Time conversion: {published_at} (UTC) -> {time_str} ({user_timezone}) for category {category}")
                logger.info(f"Original time: {pub_time}, Local time: {local_time}")
            except Exception as e:
                logger.error(f"Error formatting time: {e}")
                time_str = 'N/A'
            
            formatted_articles.append({
                'title': title,
                'description': description,
                'url': url,
                'source': source,
                'time': time_str,
                'published_at': published_at,
                'image_url': image_url
            })
        
        return {
            'category': category,
            'category_name': NEWS_CATEGORIES[category]["name"],
            'category_emoji': NEWS_CATEGORIES[category]["emoji"],
            'articles': formatted_articles,
            'total_results': len(formatted_articles)
        }
    
    def format_news_message(self, news_data: Dict, page: int = 0, articles_per_page: int = 5) -> str:
        """
        Format news data into a readable message
        
        Args:
            news_data: Formatted news data
            page: Page number (0-based)
            articles_per_page: Number of articles per page
            
        Returns:
            Formatted news message
        """
        if not news_data or 'articles' not in news_data:
            return "❌ Извини, не удалось получить новости."
        
        articles = news_data['articles']
        total_articles = len(articles)
        
        if total_articles == 0:
            return f"📰 **{news_data['category_emoji']} {news_data['category_name']}**\n\nНовости не найдены."
        
        # Calculate pagination
        start_idx = page * articles_per_page
        end_idx = start_idx + articles_per_page
        page_articles = articles[start_idx:end_idx]
        
        total_pages = (total_articles + articles_per_page - 1) // articles_per_page
        
        # Create message header
        message = f"📰 <b>{news_data['category_emoji']} {news_data['category_name']}</b>"
        if total_pages > 1:
            message += f" (стр. {page + 1}/{total_pages})"
        message += "\n\n"
        
        # Add articles
        for i, article in enumerate(page_articles, start=start_idx + 1):
            message += f"<b>{i}. {article['title']}</b>\n"
            if article['description']:
                # Truncate description if too long
                desc = article['description']
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                message += f"<blockquote>{desc}</blockquote>\n"
            message += "\n"
        
        return message
    
    def get_news_categories(self) -> Dict:
        """Get available news categories"""
        return NEWS_CATEGORIES
    
    def get_latest_news(self, user_timezone: str = "UTC") -> Optional[Dict]:
        """Get latest news (default category)"""
        return self.get_news("latest", user_timezone)
    
    def format_news_details(self, news_data: Dict, article_index: int) -> str:
        """
        Format detailed news article
        
        Args:
            news_data: Formatted news data
            article_index: Index of the article (1-based)
            
        Returns:
            Formatted news details message
        """
        if not news_data or 'articles' not in news_data:
            return "❌ Извини, не удалось получить новости."
        
        articles = news_data['articles']
        if article_index < 1 or article_index > len(articles):
            return "❌ Новость не найдена."
        
        article = articles[article_index - 1]  # Convert to 0-based index
        
        message = f"📰 <b>{news_data['category_emoji']} {news_data['category_name']}</b>\n\n"
        message += f"<b>{article_index}. {article['title']}</b>\n\n"
        
        if article['description']:
            # Show full description without truncation
            message += f"<blockquote>{article['description']}</blockquote>\n\n"
            # Log description length for debugging
            logger.info(f"Article description length: {len(article['description'])} characters")
        
        message += f"📰 <b>Источник:</b> {article['source']}\n"
        message += f"⏰ <b>Время:</b> {article['time']}\n"
        message += f"🔗 <b>Ссылка:</b> <a href=\"{article['url']}\">Читать статью</a>"
        
        # Log total message length for debugging
        logger.info(f"Total message length: {len(message)} characters")
        
        # Check Telegram caption limit (1024 characters)
        if len(message) > 1024:
            logger.warning(f"Message too long ({len(message)} chars), truncating description")
            # Truncate description to fit within Telegram limits
            max_description_length = 1024 - len(message) + len(article.get('description', ''))
            if max_description_length > 100:  # Ensure we have some description
                truncated_description = article['description'][:max_description_length-3] + "..."
                message = f"📰 <b>{news_data['category_emoji']} {news_data['category_name']}</b>\n\n"
                message += f"<b>{article_index}. {article['title']}</b>\n\n"
                message += f"<blockquote>{truncated_description}</blockquote>\n\n"
                message += f"📰 <b>Источник:</b> {article['source']}\n"
                message += f"⏰ <b>Время:</b> {article['time']}\n"
                message += f"🔗 <b>Ссылка:</b> <a href=\"{article['url']}\">Читать статью</a>"
                logger.info(f"Truncated message length: {len(message)} characters")
        
        return message


# Global instance
news_service = NewsService()
