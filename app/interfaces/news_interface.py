"""
News interface module for Teo bot
Provides interactive keyboards for news navigation
"""
from typing import List, Dict, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.services.news_service import news_service


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
        
        # Numbered buttons for latest news (1-3) with navigation buttons in the same row
        article_buttons = []
        start_article = page * 3 + 1  # Calculate starting article number for this page
        
        # Add back button first if not on first page
        if page > 0:
            article_buttons.append(InlineKeyboardButton("⬅️", callback_data=f'news_page_latest_{page - 1}'))
        
        # Add numbered buttons
        for i in range(3):  # 3 articles per page
            article_number = start_article + i
            article_buttons.append(InlineKeyboardButton(str(article_number), callback_data=f'news_details_latest_{page}_{article_number}'))
        
        # Add next button if not on last page
        if page < total_pages - 1:
            article_buttons.append(InlineKeyboardButton("➡️", callback_data=f'news_page_latest_{page + 1}'))
        
        keyboard.append(article_buttons)
        
        # Category label (non-active button)
        keyboard.append([InlineKeyboardButton("📰 Категории", callback_data='no_action')])
        
        # Category buttons with emoji icons only (compact layout) + search button
        keyboard.append([
            InlineKeyboardButton("🔥", callback_data='news_category_popular'),
            InlineKeyboardButton("⚽", callback_data='news_category_sports'),
            InlineKeyboardButton("💰", callback_data='news_category_economy'),
            InlineKeyboardButton("🤖", callback_data='news_category_technology'),
            InlineKeyboardButton("🔍", callback_data='news_search')
        ])
        
        # Update and Main menu buttons on the same row (Главное меню слева, Обновить справа)
        keyboard.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu'),
            InlineKeyboardButton("🔄 Обновить", callback_data='news_category_latest')
        ])
        
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
        
        # Numbered buttons for articles (adapt to page) with navigation buttons in the same row
        article_buttons = []
        start_article = page * 3 + 1  # Calculate starting article number for this page
        
        # Add back button first if not on first page
        if page > 0:
            article_buttons.append(InlineKeyboardButton("⬅️", callback_data=f'news_page_{category}_{page - 1}'))
        
        # Add numbered buttons
        for i in range(3):  # 3 articles per page
            article_number = start_article + i
            article_buttons.append(InlineKeyboardButton(str(article_number), callback_data=f'news_details_{category}_{page}_{article_number}'))
        
        # Add next button if not on last page
        if page < total_pages - 1:
            article_buttons.append(InlineKeyboardButton("➡️", callback_data=f'news_page_{category}_{page + 1}'))
        
        keyboard.append(article_buttons)
        
        # Action buttons - compact layout
        keyboard.append([
            InlineKeyboardButton("🔄 Обновить", callback_data=f'news_category_{category}'),
            InlineKeyboardButton("📰 К меню новостей", callback_data='news_menu')
        ])
        
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
            article_index: Article index (1-3)
            
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
    def get_page_count(articles_count: int, articles_per_page: int = 3) -> int:
        """Get total number of pages for articles"""
        return (articles_count + articles_per_page - 1) // articles_per_page
