"""
News interface module for Teo bot
Provides interactive keyboards for news navigation
"""
from typing import List, Dict, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.services.news_service import news_service


class NewsInterface:
    """Handles interactive news interfaces"""
    
    @staticmethod
    def create_main_news_menu() -> InlineKeyboardMarkup:
        """Create main news menu with category buttons (excluding latest)"""
        categories = news_service.get_news_categories()
        
        keyboard = []
        
        # Add category buttons (2 per row), excluding "latest"
        category_items = [(k, v) for k, v in categories.items() if k != "latest"]
        for i in range(0, len(category_items), 2):
            row = []
            category_key, category_data = category_items[i]
            row.append(InlineKeyboardButton(
                f"{category_data['emoji']} {category_data['name']}", 
                callback_data=f'news_category_{category_key}'
            ))
            
            if i + 1 < len(category_items):
                next_category_key, next_category_data = category_items[i + 1]
                row.append(InlineKeyboardButton(
                    f"{next_category_data['emoji']} {next_category_data['name']}", 
                    callback_data=f'news_category_{next_category_key}'
                ))
            
            keyboard.append(row)
        
        # Back button
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_news_main_menu(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
        """Create news main menu with specific buttons as requested"""
        keyboard = []
        
        # Numbered buttons for latest news (1-5 for first page)
        article_buttons = []
        start_article = page * 5 + 1  # Calculate starting article number for this page
        for i in range(5):  # 5 articles per page
            article_number = start_article + i
            article_buttons.append(InlineKeyboardButton(str(article_number), callback_data=f'news_details_latest_{page}_{article_number}'))
        keyboard.append(article_buttons)
        
        # Update button
        keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data='news_category_latest')])
        
        # Navigation row (Next button for scrolling through news)
        nav_row = []
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'news_page_latest_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Category buttons (2 per row)
        keyboard.append([
            InlineKeyboardButton("📰 Главные новости", callback_data='news_category_popular'),
            InlineKeyboardButton("⚽ Спорт", callback_data='news_category_sports')
        ])
        
        keyboard.append([
            InlineKeyboardButton("💰 Экономика и бизнес", callback_data='news_category_economy'),
            InlineKeyboardButton("🤖 Технологии и наука", callback_data='news_category_technology')
        ])
        
        # Main menu button
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_news_navigation_keyboard(category: str, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
        """
        Create navigation keyboard for news articles with numbered buttons
        
        Args:
            category: News category
            page: Current page number
            total_pages: Total number of pages
            
        Returns:
            InlineKeyboardMarkup
        """
        keyboard = []
        
        # Numbered buttons for articles (adapt to page)
        article_buttons = []
        start_article = page * 5 + 1  # Calculate starting article number for this page
        for i in range(5):  # 5 articles per page
            article_number = start_article + i
            article_buttons.append(InlineKeyboardButton(str(article_number), callback_data=f'news_details_{category}_{page}_{article_number}'))
        keyboard.append(article_buttons)
        
        # Navigation row
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'news_page_{category}_{page - 1}'))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'news_page_{category}_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Action buttons - separate buttons
        keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data=f'news_category_{category}')])
        keyboard.append([InlineKeyboardButton("📰 К меню новостей", callback_data='news_menu')])
        
        # Back button
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_news_details_keyboard(category: str, page: int, article_index: int) -> InlineKeyboardMarkup:
        """
        Create keyboard for news details view
        
        Args:
            category: News category
            page: Current page number
            article_index: Article index (1-5)
            
        Returns:
            InlineKeyboardMarkup
        """
        keyboard = []
        
        # Back to news list button
        keyboard.append([InlineKeyboardButton("🔙 К списку новостей", callback_data=f'news_page_{category}_{page}')])
        
        # Action buttons
        keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data=f'news_category_{category}')])
        keyboard.append([InlineKeyboardButton("📰 К меню новостей", callback_data='news_menu')])
        
        # Main menu button
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_page_count(articles_count: int, articles_per_page: int = 5) -> int:
        """Get total number of pages for articles"""
        return (articles_count + articles_per_page - 1) // articles_per_page
