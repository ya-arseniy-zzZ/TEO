"""
Keyboard utilities for Teo bot
Eliminates code duplication by providing reusable keyboard builders
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional


class KeyboardBuilder:
    """Utility class for building Telegram inline keyboards"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Create main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
            [InlineKeyboardButton("📰 Новости", callback_data='news_menu')],
            [InlineKeyboardButton("🎯 Привычки", callback_data='habits_menu')],
            [InlineKeyboardButton("💰 Финансы", callback_data='finance_menu')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Create back to main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def weather_menu() -> InlineKeyboardMarkup:
        """Create weather menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🌤 Текущая погода", callback_data='current_weather')],
            [InlineKeyboardButton("📅 Прогноз на 3 дня", callback_data='forecast')],
            [InlineKeyboardButton("🌧 Настройки дождя", callback_data='rain_settings')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def weather_actions() -> InlineKeyboardMarkup:
        """Create weather actions keyboard"""
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='current_weather')],
            [InlineKeyboardButton("📅 Прогноз на 3 дня", callback_data='forecast')],
            [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu'),
             InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def forecast_actions() -> InlineKeyboardMarkup:
        """Create forecast actions keyboard"""
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить прогноз", callback_data='forecast')],
            [InlineKeyboardButton("🌤 Текущая погода", callback_data='current_weather')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Create settings menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🔔 Уведомления", callback_data='notifications_menu')],
            [InlineKeyboardButton("🌍 Город", callback_data='change_city')],
            [InlineKeyboardButton("⏰ Время", callback_data='change_time')],
            [InlineKeyboardButton("🌐 Часовой пояс", callback_data='settings_timezone')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def notifications_menu() -> InlineKeyboardMarkup:
        """Create notifications menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🔔 Ежедневные уведомления", callback_data='toggle_daily_notifications')],
            [InlineKeyboardButton("🌧 Уведомления о дожде", callback_data='toggle_rain_alerts')],
            [InlineKeyboardButton("⏰ Изменить время", callback_data='change_time')],
            [InlineKeyboardButton("🔙 Назад", callback_data='settings')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def habits_menu() -> InlineKeyboardMarkup:
        """Create habits menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("📋 Мои привычки", callback_data='view_habits')],
            [InlineKeyboardButton("➕ Создать привычку", callback_data='create_habit')],
            [InlineKeyboardButton("📊 Статистика", callback_data='habit_stats')],
            [InlineKeyboardButton("⚙️ Управление", callback_data='manage_habits')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def finance_menu() -> InlineKeyboardMarkup:
        """Create finance menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("📊 Анализ за месяц", callback_data='finance_month')],
            [InlineKeyboardButton("📈 Анализ за неделю", callback_data='finance_week')],
            [InlineKeyboardButton("📅 Анализ за день", callback_data='finance_day')],
            [InlineKeyboardButton("💰 Общий анализ", callback_data='finance_all')],
            [InlineKeyboardButton("⚙️ Настройки таблицы", callback_data='finance_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def finance_settings() -> InlineKeyboardMarkup:
        """Create finance settings keyboard"""
        keyboard = [
            [InlineKeyboardButton("📝 Указать ссылку на таблицу", callback_data='finance_set_url')],
            [InlineKeyboardButton("🔗 Показать текущую ссылку", callback_data='finance_show_url')],
            [InlineKeyboardButton("❌ Удалить настройки", callback_data='finance_clear_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def error_back(back_callback: str = 'main_menu') -> InlineKeyboardMarkup:
        """Create error back keyboard"""
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data=back_callback)]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def custom_keyboard(buttons: List[List[InlineKeyboardButton]], 
                       include_main_menu: bool = True) -> InlineKeyboardMarkup:
        """Create custom keyboard with optional main menu button"""
        keyboard = buttons.copy()
        if include_main_menu:
            keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
        return InlineKeyboardMarkup(keyboard)
