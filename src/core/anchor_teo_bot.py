"""
Teo - Personal Assistant Telegram Bot with Anchor-UX
Main bot implementation with Anchor-UX system
"""
import logging
import asyncio
import sys
import os
from datetime import datetime, time, timedelta
from typing import Dict, Set, List, Optional, Any
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters,
    ContextTypes
)

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.config import BOT_TOKEN, DEFAULT_CITY, TIMEZONE
from src.services.weather_service import WeatherService
from src.services.notification_scheduler import NotificationScheduler
from src.services.rain_monitor import RainMonitor
from src.interfaces.interactive_settings import InteractiveSettings
from src.services.habit_tracker import HabitTracker
from src.interfaces.habit_interface import HabitInterface
from src.services.news_service import news_service
from src.interfaces.news_interface import NewsInterface
from src.interfaces.finance_interface import FinanceInterface
from src.database.database import DatabaseManager
from src.database.migration import run_migration
from src.utils.keyboards import KeyboardBuilder
from src.utils.messages import MessageBuilder
from src.utils.anchor_ux import anchor_ux_manager, InputType
from src.utils.anchor_helpers import (
    show_screen, show_main_menu, handle_navigation_callback,
    handle_text_input, answer_callback_query_safely, show_loading_screen
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global instances
weather_service = WeatherService()
scheduler = NotificationScheduler()
rain_monitor = RainMonitor()
habit_tracker = HabitTracker()
db = DatabaseManager()


class AnchorTeoBot:
    """Main bot class with Anchor-UX system"""
    
    def __init__(self):
        self.application = None
        self.notification_users: Set[int] = set()
        self._setup_anchor_handlers()
    
    def _setup_anchor_handlers(self):
        """Setup Anchor-UX callback handlers"""
        # Navigation handlers
        anchor_ux_manager.register_callback_handler("nav_back", self._handle_nav_back)
        anchor_ux_manager.register_callback_handler("nav_main", self._handle_nav_main)
        anchor_ux_manager.register_callback_handler("hide_notification", self._handle_hide_notification)
        
        # Main menu handlers
        anchor_ux_manager.register_callback_handler("weather_menu", self._handle_weather_menu)
        anchor_ux_manager.register_callback_handler("news_menu", self._handle_news_menu)
        anchor_ux_manager.register_callback_handler("habits_menu", self._handle_habits_menu)
        anchor_ux_manager.register_callback_handler("finance_menu", self._handle_finance_menu)
        anchor_ux_manager.register_callback_handler("settings", self._handle_settings)
        anchor_ux_manager.register_callback_handler("help", self._handle_help)
        
        # Weather handlers
        anchor_ux_manager.register_callback_handler("current_weather", self._handle_current_weather)
        anchor_ux_manager.register_callback_handler("forecast", self._handle_forecast)
        anchor_ux_manager.register_callback_handler("rain_settings", self._handle_rain_settings)
        
        # Finance handlers
        anchor_ux_manager.register_callback_handler("finance_connect", self._handle_finance_connect)
        anchor_ux_manager.register_callback_handler("finance_settings", self._handle_finance_settings)
        anchor_ux_manager.register_callback_handler("finance_analyze", self._handle_finance_analyze)
        
        # Habits handlers
        anchor_ux_manager.register_callback_handler("view_habits", self._handle_view_habits)
        anchor_ux_manager.register_callback_handler("create_habit", self._handle_create_habit)
        anchor_ux_manager.register_callback_handler("habit_stats", self._handle_habit_stats)
        
        # Settings handlers
        anchor_ux_manager.register_callback_handler("notifications_menu", self._handle_notifications_menu)
        anchor_ux_manager.register_callback_handler("toggle_notifications", self._handle_toggle_notifications)
        anchor_ux_manager.register_callback_handler("test_notification", self._handle_test_notification)
        anchor_ux_manager.register_callback_handler("change_city", self._handle_change_city)
        anchor_ux_manager.register_callback_handler("change_time", self._handle_change_time)
        
        # Generic handlers
        anchor_ux_manager.register_callback_handler("retry_input", self._handle_retry_input)
        anchor_ux_manager.register_callback_handler("no_action", self._handle_no_action)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command with Anchor-UX"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        # Initialize user in database
        db.create_or_update_user(
            user_id=user_id,
            username=update.effective_user.username,
            first_name=user_name
        )
        
        # Get weather settings from database
        weather_settings = db.get_weather_settings(user_id)
        if weather_settings and weather_settings.get('rain_alerts_enabled'):
            rain_monitor.enable_rain_alerts(user_id, weather_settings)
        
        # Create main menu screen
        await show_main_menu(update, context)
        
        # Save anchor message ID to database
        anchor_message_id = anchor_ux_manager.get_anchor_message_id(user_id, update.effective_chat.id)
        if anchor_message_id:
            db.save_user_main_message(user_id, anchor_message_id)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        await self._handle_help(update, context)
    
    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /debug command"""
        user_id = update.effective_user.id
        
        # Get scheduler debug info
        scheduler_debug = scheduler.debug_scheduler_status()
        
        # Get user settings
        weather_settings = db.get_weather_settings(user_id)
        user_info = f"""
User ID: {user_id}
Weather Settings: {weather_settings}
Notifications Enabled: {weather_settings.get('daily_notifications_enabled', False) if weather_settings else False}
Notification Time: {weather_settings.get('notification_time', 'Not set') if weather_settings else 'Not set'}
"""
        
        debug_text = f"🔧 **Отладочная информация**\n\n{user_info}\n{scheduler_debug}"
        
        await update.message.reply_text(debug_text, parse_mode='Markdown')
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries with Anchor-UX"""
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        
        # Update session activity
        anchor_ux_manager.update_session_activity(user_id, chat_id)
        
        # Answer callback query immediately
        await answer_callback_query_safely(update)
        
        # Parse callback data
        callback_data = query.data
        
        # Handle navigation callbacks first
        if callback_data.startswith("nav_"):
            await handle_navigation_callback(update, context, callback_data)
            return
        
        # Try to handle with registered handlers
        handled = await anchor_ux_manager.handle_callback(update, context, callback_data)
        
        if not handled:
            # Fallback to legacy handlers
            await self._handle_legacy_callback(update, context, callback_data)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages with Anchor-UX"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Update session activity
        anchor_ux_manager.update_session_activity(user_id, chat_id)
        
        # Try to handle as text input
        handled = await handle_text_input(update, context)
        
        if not handled:
            # Show main menu if no specific input handling
            await show_main_menu(update, context)
    
    # Navigation handlers
    async def _handle_nav_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle back navigation"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        previous_screen = anchor_ux_manager.go_back(user_id, chat_id)
        if previous_screen:
            await show_screen(update, context, previous_screen)
        else:
            await show_main_menu(update, context)
    
    async def _handle_nav_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle main menu navigation"""
        await show_main_menu(update, context)
    
    async def _handle_hide_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle hide notification"""
        try:
            await update.callback_query.message.delete()
        except Exception as e:
            logger.error(f"Error hiding notification: {e}")
    
    # Main menu handlers
    async def _handle_weather_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle weather menu"""
        from src.utils.anchor_ux import ScreenState
        
        screen = ScreenState(
            screen_id="weather_menu",
            params=params,
            title="🌤 Погода",
            content="Выберите действие:",
            status="",
            keyboard=[
                [{"text": "🌤 Текущая погода", "callback_data": "current_weather"}],
                [{"text": "📅 Прогноз на 3 дня", "callback_data": "forecast"}],
                [{"text": "🌧 Настройки дождя", "callback_data": "rain_settings"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_news_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle news menu"""
        from src.utils.anchor_ux import ScreenState
        
        screen = ScreenState(
            screen_id="news_menu",
            params=params,
            title="📰 Новости",
            content="Выберите категорию новостей:",
            status="",
            keyboard=[
                [{"text": "📰 Главные новости", "callback_data": "news_main"}],
                [{"text": "⚽ Спорт", "callback_data": "news_sport"}],
                [{"text": "💰 Экономика", "callback_data": "news_economy"}],
                [{"text": "🔬 Технологии", "callback_data": "news_tech"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_habits_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle habits menu"""
        from src.utils.anchor_ux import ScreenState
        
        screen = ScreenState(
            screen_id="habits_menu",
            params=params,
            title="🎯 Привычки",
            content="Управление привычками:",
            status="",
            keyboard=[
                [{"text": "📋 Мои привычки", "callback_data": "view_habits"}],
                [{"text": "➕ Создать привычку", "callback_data": "create_habit"}],
                [{"text": "📊 Статистика", "callback_data": "habit_stats"}],
                [{"text": "⚙️ Управление", "callback_data": "manage_habits"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_finance_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle finance menu"""
        from src.utils.anchor_ux import ScreenState
        
        user_id = update.effective_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        if finance_settings:
            status = "✅ Таблица подключена"
            content = "Финансовый анализ готов к работе."
            keyboard = [
                [{"text": "📊 Анализ", "callback_data": "finance_analyze"}],
                [{"text": "⚙️ Настройки", "callback_data": "finance_settings"}]
            ]
        else:
            status = "❌ Таблица не подключена"
            content = "Для анализа финансов нужно подключить Google Таблицу."
            keyboard = [
                [{"text": "🔗 Подключить таблицу", "callback_data": "finance_connect"}]
            ]
        
        screen = ScreenState(
            screen_id="finance_menu",
            params=params,
            title="💰 Финансы",
            content=content,
            status=status,
            keyboard=keyboard,
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle settings menu"""
        from src.utils.anchor_ux import ScreenState
        
        screen = ScreenState(
            screen_id="settings",
            params=params,
            title="⚙️ Настройки",
            content="Настройки бота:",
            status="",
            keyboard=[
                [{"text": "🔔 Уведомления", "callback_data": "notifications_menu"}],
                [{"text": "🌍 Город", "callback_data": "change_city"}],
                [{"text": "⏰ Время", "callback_data": "change_time"}],
                [{"text": "🌐 Часовой пояс", "callback_data": "settings_timezone"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle help menu"""
        from src.utils.anchor_ux import ScreenState
        
        screen = ScreenState(
            screen_id="help",
            params=params,
            title="❓ Помощь",
            content=MessageBuilder.help_message(),
            status="",
            keyboard=[],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    # Weather handlers
    async def _handle_current_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle current weather request"""
        user_id = update.effective_user.id
        
        # Show loading screen
        await show_loading_screen(update, context, "Получаю данные о погоде...")
        
        try:
            # Get user's city
            user_settings = db.get_weather_settings(user_id)
            city = user_settings.get('city', DEFAULT_CITY) if user_settings else DEFAULT_CITY
            
            # Get weather data
            weather_data = await weather_service.get_current_weather(city)
            
            if weather_data:
                from src.utils.anchor_ux import ScreenState
                
                # Format weather message
                weather_text = f"""
🌤 **Погода в {city}**

🌡 Температура: {weather_data['temperature']}°C
🌡 Ощущается как: {weather_data['feels_like']}°C
💨 Ветер: {weather_data['wind_speed']} м/с
💧 Влажность: {weather_data['humidity']}%
☁️ Облачность: {weather_data['description']}

🕐 Обновлено: {weather_data['timestamp']}
"""
                
                screen = ScreenState(
                    screen_id="current_weather",
                    params={"city": city},
                    title=f"🌤 Погода в {city}",
                    content=weather_text,
                    status=f"Обновлено: {weather_data['timestamp']}",
                    keyboard=[
                        [{"text": "🔄 Обновить", "callback_data": "current_weather"}],
                        [{"text": "📅 Прогноз", "callback_data": "forecast"}]
                    ],
                    created_at=datetime.now()
                )
                
                await show_screen(update, context, screen)
            else:
                # Show error
                from src.utils.anchor_ux import ScreenState
                screen = ScreenState(
                    screen_id="weather_error",
                    params={},
                    title="❌ Ошибка",
                    content="Не удалось получить данные о погоде.",
                    status="",
                    keyboard=[
                        [{"text": "🔄 Попробовать снова", "callback_data": "current_weather"}],
                        [{"text": "🔙 Назад", "callback_data": "weather_menu"}]
                    ],
                    created_at=datetime.now()
                )
                
                await show_screen(update, context, screen)
                
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            # Show error screen
            from src.utils.anchor_ux import ScreenState
            screen = ScreenState(
                screen_id="weather_error",
                params={},
                title="❌ Ошибка",
                content="Произошла ошибка при получении погоды.",
                status="",
                keyboard=[
                    [{"text": "🔄 Попробовать снова", "callback_data": "current_weather"}],
                    [{"text": "🔙 Назад", "callback_data": "weather_menu"}]
                ],
                created_at=datetime.now()
            )
            
            await show_screen(update, context, screen)
    
    async def _handle_forecast(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle weather forecast request"""
        # Similar to current weather but for forecast
        await self._handle_current_weather(update, context, params)  # Placeholder
    
    async def _handle_rain_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle rain settings"""
        # Placeholder for rain settings
        pass
    
    # Finance handlers
    async def _handle_finance_connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle finance table connection"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Set awaiting input for Google Sheets URL
        anchor_ux_manager.set_awaiting_input(
            user_id, chat_id,
            InputType.URL,
            "ссылку на Google Таблицу",
            context={"finance_sheet": True}
        )
        
        from src.utils.anchor_ux import ScreenState
        screen = ScreenState(
            screen_id="finance_connect",
            params=params,
            title="🔗 Подключение таблицы",
            content="Жду ссылку на Google Таблицу с правом 'Просмотр по ссылке'.\n\nПришли URL одним сообщением.",
            status="",
            keyboard=[
                [{"text": "❓ Пример", "callback_data": "finance_example"}],
                [{"text": "🔙 Отмена", "callback_data": "finance_menu"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_finance_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle finance settings"""
        # Placeholder for finance settings
        pass
    
    async def _handle_finance_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle finance analysis"""
        # Placeholder for finance analysis
        pass
    
    # Habits handlers
    async def _handle_view_habits(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle view habits"""
        # Placeholder for view habits
        pass
    
    async def _handle_create_habit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle create habit"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Set awaiting input for habit name
        anchor_ux_manager.set_awaiting_input(
            user_id, chat_id,
            InputType.TEXT,
            "название привычки",
            context={"habit_name": True}
        )
        
        from src.utils.anchor_ux import ScreenState
        screen = ScreenState(
            screen_id="habit_create",
            params=params,
            title="➕ Создание привычки",
            content="Введите название новой привычки:",
            status="",
            keyboard=[
                [{"text": "🔙 Отмена", "callback_data": "habits_menu"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_habit_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle habit statistics"""
        # Placeholder for habit stats
        pass
    
    # Settings handlers
    async def _handle_notifications_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle notifications menu"""
        user_id = update.effective_user.id
        weather_settings = db.get_weather_settings(user_id)
        
        if weather_settings:
            notifications_enabled = weather_settings.get('daily_notifications_enabled', False)
            notification_time = weather_settings.get('notification_time', '08:00')
            city = weather_settings.get('city', DEFAULT_CITY)
        else:
            notifications_enabled = False
            notification_time = '08:00'
            city = DEFAULT_CITY
        
        status = "🟢 Включены" if notifications_enabled else "🔴 Отключены"
        
        content = f"""📋 **Настройки уведомлений**

**Статус:** {status}
**Время:** {notification_time}
**Город:** {city}

Используй кнопки ниже для управления уведомлениями:"""
        
        from src.utils.anchor_ux import ScreenState
        screen = ScreenState(
            screen_id="notifications_menu",
            params=params,
            title="🔔 Уведомления",
            content=content,
            status="",
            keyboard=[
                [{"text": "🔴 Отключить" if notifications_enabled else "🟢 Включить", "callback_data": "toggle_notifications"}],
                [{"text": "⏰ Изменить время", "callback_data": "change_time"}],
                [{"text": "🌍 Изменить город", "callback_data": "change_city"}],
                [{"text": "🔄 Тестовое уведомление", "callback_data": "test_notification"}],
                [{"text": "🔙 Назад", "callback_data": "settings"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_toggle_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle toggle notifications"""
        user_id = update.effective_user.id
        weather_settings = db.get_weather_settings(user_id)
        current_status = weather_settings.get('daily_notifications_enabled', False) if weather_settings else False
        new_status = not current_status
        
        # Update in database
        db.update_weather_settings(user_id, daily_notifications_enabled=new_status)
        
        if new_status:
            # Enable daily notifications
            updated_settings = db.get_weather_settings(user_id)
            if updated_settings:
                scheduler.add_user(user_id, updated_settings)
        else:
            # Disable daily notifications
            scheduler.remove_user(user_id)
        
        # Show updated notifications menu
        await self._handle_notifications_menu(update, context, params)
    
    async def _handle_test_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle test notification"""
        user_id = update.effective_user.id
        
        try:
            await self.send_weather_notification(user_id)
            
            from src.utils.anchor_ux import ScreenState
            screen = ScreenState(
                screen_id="test_notification",
                params=params,
                title="✅ Тестовое уведомление",
                content="Тестовое уведомление отправлено! Проверь свои сообщения.",
                status="success",
                keyboard=[
                    [{"text": "🔙 Назад к уведомлениям", "callback_data": "notifications_menu"}]
                ],
                created_at=datetime.now()
            )
            
            await show_screen(update, context, screen)
            
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            
            from src.utils.anchor_ux import ScreenState
            screen = ScreenState(
                screen_id="test_notification",
                params=params,
                title="❌ Ошибка",
                content=f"Не удалось отправить тестовое уведомление: {str(e)}",
                status="error",
                keyboard=[
                    [{"text": "🔙 Назад к уведомлениям", "callback_data": "notifications_menu"}]
                ],
                created_at=datetime.now()
            )
            
            await show_screen(update, context, screen)
    
    async def _handle_change_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle change city"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Set awaiting input for city name
        anchor_ux_manager.set_awaiting_input(
            user_id, chat_id,
            InputType.TEXT,
            "название города",
            context={"city_name": True}
        )
        
        from src.utils.anchor_ux import ScreenState
        screen = ScreenState(
            screen_id="change_city",
            params=params,
            title="🌍 Изменение города",
            content="Введите название города:",
            status="",
            keyboard=[
                [{"text": "🔙 Отмена", "callback_data": "settings"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    async def _handle_change_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle change time"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Set awaiting input for time
        anchor_ux_manager.set_awaiting_input(
            user_id, chat_id,
            InputType.TIME,
            "время уведомлений (HH:MM)",
            context={"notification_time": True}
        )
        
        from src.utils.anchor_ux import ScreenState
        screen = ScreenState(
            screen_id="change_time",
            params=params,
            title="⏰ Изменение времени",
            content="Введите время уведомлений в формате HH:MM:",
            status="",
            keyboard=[
                [{"text": "🔙 Отмена", "callback_data": "notifications_menu"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
    
    # Generic handlers
    async def _handle_retry_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle retry input"""
        # Go back to previous screen to retry input
        await self._handle_nav_back(update, context, params)
    
    async def _handle_no_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, params: Dict[str, Any]):
        """Handle no action callback (for pagination info)"""
        # Do nothing, just answer the callback
        pass
    
    async def _handle_legacy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle legacy callback data format"""
        # Fallback for old callback data format
        logger.warning(f"Legacy callback data: {callback_data}")
        await show_main_menu(update, context)
    
    async def setup(self):
        """Setup bot application"""
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("debug", self.debug_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Set bot commands
        await self.application.bot.set_my_commands([
            BotCommand("start", "Запустить бота"),
            BotCommand("help", "Показать справку")
        ])
        
        # Initialize database
        run_migration()
        
        # Set up notification scheduler
        scheduler.set_notification_callback(self.send_weather_notification)
        
        # Set up rain monitoring
        rain_monitor.set_rain_callback(self.send_rain_alert)
        
        # Set up habit tracking
        habit_tracker.set_reminder_callback(self.send_habit_reminder)
        
        # Load existing users with notifications enabled
        self._load_existing_notification_users()
        self._load_existing_rain_alert_users()
        
        # Start services
        scheduler.start_scheduler()
        rain_monitor.start_monitoring()
        habit_tracker.start_monitoring()
        
        logger.info("Anchor Teo Bot setup completed")
    
    async def start(self):
        """Start the bot"""
        await self.setup()
        await self.application.initialize()
        await self.application.start()
        await self.application.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False, stop_signals=None)
    
    async def send_weather_notification(self, user_id: int) -> None:
        """Send weather notification to a user"""
        try:
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            
            weather_data = weather_service.get_current_weather(city)
            
            if weather_data:
                notification_message = f"🌅 **Доброе утро! Вот твоя ежедневная сводка погоды:**\n\n{weather_service.format_weather_message(weather_data)}"
                
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=notification_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Weather notification sent to user {user_id}")
            else:
                logger.error(f"Failed to fetch weather data for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
    
    async def send_rain_alert(self, user_id: int, message: str) -> None:
        """Send rain alert to a user"""
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Rain alert sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending rain alert to user {user_id}: {e}")
    
    async def send_habit_reminder(self, habit_data: Dict) -> None:
        """Send habit reminder to a user"""
        try:
            user_id = habit_data.get('user_id')
            habit_name = habit_data.get('name', 'Привычка')
            
            message = f"🎯 **Напоминание о привычке:** {habit_name}\n\nНе забудь выполнить свою привычку!"
            
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Habit reminder sent to user {user_id} for habit {habit_name}")
        except Exception as e:
            logger.error(f"Error sending habit reminder: {e}")
    
    async def stop(self):
        """Stop the bot"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        scheduler.stop_scheduler()
        rain_monitor.stop_monitoring()
        habit_tracker.stop_monitoring()
        
        logger.info("Anchor Teo Bot stopped")
    
    def _load_existing_notification_users(self):
        """Load existing users with notifications enabled into scheduler"""
        try:
            # Get users with daily notifications enabled
            users_with_notifications = db.get_users_with_daily_notifications()
            
            for user in users_with_notifications:
                user_id = user.get('user_id')
                if user_id:
                    # Create weather settings dict from user data
                    weather_settings = {
                        'city': user.get('city', DEFAULT_CITY),
                        'timezone': user.get('timezone', TIMEZONE),
                        'daily_notifications_enabled': user.get('daily_notifications_enabled', False),
                        'notification_time': user.get('notification_time', '08:00'),
                        'rain_alerts_enabled': user.get('rain_alerts_enabled', True)
                    }
                    
                    scheduler.add_user(user_id, weather_settings)
                    logger.info(f"Loaded user {user_id} with notifications enabled at {weather_settings['notification_time']}")
            
            logger.info(f"Loaded {len(users_with_notifications)} users with notifications enabled")
            
        except Exception as e:
            logger.error(f"Error loading existing notification users: {e}")
    
    def _load_existing_rain_alert_users(self):
        """Load existing users with rain alerts enabled into rain monitor"""
        try:
            # Get users with rain alerts enabled
            users_with_rain_alerts = db.get_users_with_rain_alerts()
            
            for user in users_with_rain_alerts:
                user_id = user.get('user_id')
                if user_id:
                    # Create weather settings dict from user data
                    weather_settings = {
                        'city': user.get('city', DEFAULT_CITY),
                        'timezone': user.get('timezone', TIMEZONE),
                        'rain_alerts_enabled': user.get('rain_alerts_enabled', True)
                    }
                    
                    rain_monitor.enable_rain_alerts(user_id, weather_settings)
                    logger.info(f"Loaded user {user_id} with rain alerts enabled for {weather_settings['city']}")
            
            logger.info(f"Loaded {len(users_with_rain_alerts)} users with rain alerts enabled")
            
        except Exception as e:
            logger.error(f"Error loading existing rain alert users: {e}")


# Global bot instance
anchor_teo_bot = AnchorTeoBot()
