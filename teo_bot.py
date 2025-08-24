"""
Teo - Personal Assistant Telegram Bot
Main bot implementation with weather notifications
"""
import logging
import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, Set, List
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, InputMediaPhoto
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters,
    ContextTypes
)

from config import BOT_TOKEN, DEFAULT_CITY, TIMEZONE
from weather_service import WeatherService
from notification_scheduler import NotificationScheduler
from rain_monitor import RainMonitor
from interactive_settings import InteractiveSettings
from habit_tracker import HabitTracker
from habit_interface import HabitInterface
import habit_methods
from news_service import news_service
from news_interface import NewsInterface
from database import DatabaseManager
from migration import run_migration

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

# User state for handling custom input (still in-memory for session data)
user_states: Dict[int, str] = {}
# Temporary habit creation data (session data)
habit_creation_data: Dict[int, Dict] = {}


class TeoBot:
    """Main bot class"""
    
    def __init__(self):
        self.application = None
        self.notification_users: Set[int] = set()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
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
        
        welcome_message = f"""👋 Привет, {user_name}! Я Тео, твой персональный помощник!

Я помогу тебе:
🌤 Получать актуальную погоду и прогнозы
📰 Читать последние новости России
🎯 Отслеживать привычки и достигать целей

Нажми кнопку ниже, чтобы начать:"""
        
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Use custom bot avatar image for start command
            with open('bot_avatar_for_start.jpeg', 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=welcome_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except FileNotFoundError:
            # Fallback to text message if image file not found
            logger.warning("Start avatar image not found, using text message")
            await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            # Fallback to text message if error
            logger.error(f"Error displaying start avatar: {e}")
            await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        await self._show_help_message(update.message)
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /weather command"""
        user_id = update.effective_user.id
        
        # Get city from command args or user settings
        if context.args:
            city = ' '.join(context.args)
        else:
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Fetch weather data
        weather_data = weather_service.get_current_weather(city)
        message = weather_service.format_weather_message(weather_data)
        
        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='current_weather')],
            [InlineKeyboardButton("📅 Прогноз на 3 дня", callback_data='forecast')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def forecast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /forecast command"""
        user_id = update.effective_user.id
        
        # Get city from command args or user settings
        if context.args:
            city = ' '.join(context.args)
        else:
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Fetch forecast data
        forecast_data = weather_service.get_weather_forecast(city)
        message = weather_service.format_forecast_message(forecast_data)
        
        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить прогноз", callback_data='forecast')],
            [InlineKeyboardButton("🌤 Текущая погода", callback_data='current_weather')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def setcity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /setcity command"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text("Пожалуйста, укажи город. Пример: `/setcity Москва`", parse_mode='Markdown')
            return
        
        city = ' '.join(context.args)
        
        # Test if the city is valid by fetching weather
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        weather_data = weather_service.get_current_weather(city)
        
        if weather_data:
            # Update city in database
            db.update_weather_settings(user_id, city=weather_data['city'])
            
            # Update rain monitoring with new city
            weather_settings = db.get_weather_settings(user_id)
            if weather_settings and weather_settings.get('rain_alerts_enabled'):
                rain_monitor.update_user_city(user_id, weather_data['city'])
            
            # Add navigation buttons
            keyboard = [
                [InlineKeyboardButton("🌤 Посмотреть погоду", callback_data='current_weather')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Твой город по умолчанию установлен: **{weather_data['city']}, {weather_data['country']}**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Извини, не могу найти данные о погоде для '{city}'. Проверь правописание и попробуй снова."
            )
    
    async def notifications_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /notifications command"""
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
        
        message = f"""📋 **Настройки уведомлений**

**Статус:** {status}
**Время:** {notification_time}
**Город:** {city}
**Часовой пояс:** {user_data.get('timezone', TIMEZONE)}

Используй кнопки ниже для управления уведомлениями:"""
        
        keyboard = [
            [InlineKeyboardButton(
                "🔴 Отключить" if notifications_enabled else "🟢 Включить",
                callback_data='toggle_notifications'
            )],
            [InlineKeyboardButton("⏰ Изменить время", callback_data='change_time'),
             InlineKeyboardButton("🌍 Изменить город", callback_data='change_city')],
            [InlineKeyboardButton("🔄 Тестовое уведомление", callback_data='test_notification')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command"""
        user_id = update.effective_user.id
        weather_settings = db.get_weather_settings(user_id)
        
        if weather_settings:
            city = weather_settings.get('city', DEFAULT_CITY)
            timezone = weather_settings.get('timezone', TIMEZONE)
            notifications_enabled = weather_settings.get('daily_notifications_enabled', False)
            notification_time = weather_settings.get('notification_time', '08:00')
            rain_alerts_enabled = weather_settings.get('rain_alerts_enabled', True)
        else:
            city = DEFAULT_CITY
            timezone = TIMEZONE
            notifications_enabled = False
            notification_time = '08:00'
            rain_alerts_enabled = True
        
        settings_text = f"""⚙️ **Твои настройки**

**Город по умолчанию:** {city}
**Часовой пояс:** {timezone}
**Уведомления:** {'🟢 Включены' if notifications_enabled else '🔴 Отключены'}
**Время уведомлений:** {notification_time}
**Уведомления о дожде:** {'🟢 Включены' if rain_alerts_enabled else '🔴 Отключены'}

Используй `/setcity <город>` чтобы изменить город по умолчанию
Используй `/timezone <часовой_пояс>` чтобы изменить часовой пояс
Используй `/notifications` для управления уведомлениями"""
        
        await update.message.reply_text(settings_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle custom text input from users"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        user_state = user_states.get(user_id)
        
        if user_state == 'waiting_city_input':
            await self._process_custom_city(update, user_id, message_text)
        elif user_state == 'waiting_time_input':
            await self._process_custom_time(update, user_id, message_text)
        elif user_state == 'waiting_habit_name':
            await self._process_custom_habit_name(update, user_id, message_text)
        elif user_state == 'waiting_habit_description':
            await self._process_habit_description(update, user_id, message_text)
        else:
            # No active state, ignore or provide help
            await update.message.reply_text(
                "Используй команды или кнопки для взаимодействия с ботом. Напиши /help для получения помощи.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ])
            )
    
    async def _process_custom_city(self, update: Update, user_id: int, city_name: str) -> None:
        """Process custom city input"""
        # Clear user state
        user_states.pop(user_id, None)
        
        # Test if the city is valid by fetching weather
        weather_data = weather_service.get_current_weather(city_name)
        
        if weather_data:
            # Update user settings
            if user_id not in user_settings:
                user_settings[user_id] = {}
            user_settings[user_id]['city'] = weather_data['city']
            
            # Update rain monitoring with new city
            if user_settings[user_id].get('rain_alerts_enabled', True):
                rain_monitor.update_user_city(user_id, weather_data['city'])
            
            message = f"✅ Город изменен на **{weather_data['city']}, {weather_data['country']}**"
            
            keyboard = [
                [InlineKeyboardButton("🌤 Посмотреть погоду", callback_data='current_weather')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            message = f"❌ Не удалось найти город '{city_name}'. Проверь правописание и попробуй ещё раз."
            
            keyboard = [
                [InlineKeyboardButton("🔙 К выбору городов", callback_data='city_page_0')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _process_custom_time(self, update: Update, user_id: int, time_str: str) -> None:
        """Process custom time input"""
        # Clear user state
        user_states.pop(user_id, None)
        
        try:
            from datetime import datetime
            datetime.strptime(time_str, '%H:%M')  # Validate time format
            
            # Update user settings
            if user_id not in user_settings:
                user_settings[user_id] = {}
            user_settings[user_id]['notification_time'] = time_str
            
            # Update scheduler if notifications are enabled
            if user_settings[user_id].get('notifications_enabled', False):
                scheduler.update_user_time(user_id, time_str)
            
            message = f"✅ Время уведомлений изменено на **{time_str}**"
            
            keyboard = [
                [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data='notifications_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except ValueError:
            message = f"❌ Неверный формат времени '{time_str}'. Используй формат ЧЧ:ММ (например, 08:30)."
            
            keyboard = [
                [InlineKeyboardButton("🔙 К выбору времени", callback_data='time_page_0')],
                [InlineKeyboardButton("🔔 К уведомлениям", callback_data='notifications_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /schedule command"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "Пожалуйста, укажи время в формате ЧЧ:ММ. Пример: `/schedule 08:30`", 
                parse_mode='Markdown'
            )
            return
        
        time_str = context.args[0]
        
        # Validate time format
        try:
            from datetime import datetime
            datetime.strptime(time_str, '%H:%M')
        except ValueError:
            await update.message.reply_text(
                "❌ Неправильный формат времени. Используй ЧЧ:ММ, например: `08:30`", 
                parse_mode='Markdown'
            )
            return
        
        # Update user settings
        if user_id not in user_settings:
            user_settings[user_id] = {}
        
        user_settings[user_id]['notification_time'] = time_str
        
        # Update scheduler if notifications are enabled
        if user_settings[user_id].get('notifications_enabled', False):
            scheduler.update_user_time(user_id, time_str)
        
        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data='notifications_menu')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Время уведомлений установлено на **{time_str}**\n\n" +
            ("Уведомления будут приходить в это время каждый день." if user_settings[user_id].get('notifications_enabled', False) 
             else "Чтобы получать уведомления, включи их командой `/notifications`"),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def timezone_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /timezone command"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                """🕰 **Установка часового пояса**
                
Пожалуйста, укажи часовой пояс. Пример: `/timezone Europe/Moscow`

**Популярные часовые пояса:**
• `Europe/Moscow` - Москва
• `Europe/Kaliningrad` - Калининград  
• `Asia/Yekaterinburg` - Екатеринбург
• `Asia/Novosibirsk` - Новосибирск
• `Asia/Krasnoyarsk` - Красноярск
• `Asia/Irkutsk` - Иркутск
• `Asia/Yakutsk` - Якутск
• `Asia/Vladivostok` - Владивосток
• `Asia/Magadan` - Магадан
• `Asia/Kamchatka` - Камчатка""", 
                parse_mode='Markdown'
            )
            return
        
        timezone_str = context.args[0]
        
        # Validate timezone
        try:
            import pytz
            pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            await update.message.reply_text(
                f"❌ Неизвестный часовой пояс: `{timezone_str}`\n\n" +
                "Используй стандартные названия, например: `Europe/Moscow`", 
                parse_mode='Markdown'
            )
            return
        
        # Update user settings
        if user_id not in user_settings:
            user_settings[user_id] = {}
        
        user_settings[user_id]['timezone'] = timezone_str
        
        # Update scheduler if notifications are enabled
        if user_settings[user_id].get('notifications_enabled', False):
            scheduler.add_user(user_id, user_settings[user_id])
        
        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Часовой пояс установлен: **{timezone_str}**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == 'main_menu':
            await self._show_main_menu(query)
        
        elif query.data == 'current_weather':
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            weather_data = weather_service.get_current_weather(city)
            message = weather_service.format_weather_message(weather_data)
            
            # Add back button
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data='current_weather')],
                [InlineKeyboardButton("📅 Прогноз на 3 дня", callback_data='forecast')],
                [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu'),
                 InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif query.data == 'forecast':
            await self._show_forecast(query, user_id)
        
        elif query.data == 'main_menu':
            await self._show_main_menu(query)
        
        elif query.data == 'weather_menu':
            await self._show_weather_menu(query, user_id)
        
        elif query.data == 'weather_menu_refresh':
            await self._show_weather_menu(query, user_id)
        
        elif query.data == 'forecast_refresh':
            await self._show_forecast(query, user_id)
        
        elif query.data == 'help':
            await self._show_help_message(query)
        
        elif query.data == 'habits_menu':
            await self._show_habits_menu(query)
        
        elif query.data == 'news_menu':
            await self._show_news_menu(query)
        
        elif query.data == 'main_settings':
            await self._show_main_settings(query, user_id)
        
        elif query.data == 'toggle_notifications':
            # Redirect to the correct handler
            await self._handle_toggle_daily_notifications(query, user_id)
        
        elif query.data == 'settings':
            try:
                weather_settings = db.get_weather_settings(user_id)
                
                if weather_settings:
                    city = weather_settings.get('city', DEFAULT_CITY)
                    notifications_enabled = weather_settings.get('daily_notifications_enabled', False)
                    notification_time = weather_settings.get('notification_time', '08:00')
                    rain_alerts_enabled = weather_settings.get('rain_alerts_enabled', True)
                else:
                    city = DEFAULT_CITY
                    notifications_enabled = False
                    notification_time = '08:00'
                    rain_alerts_enabled = True
                
                settings_text = f"""🌤 <b>Настройки погоды</b>

<blockquote><b>Город:</b> {city}
<b>Ежедневные уведомления:</b> {'🟢 Включены' if notifications_enabled else '🔴 Отключены'} ({notification_time})
<b>Уведомления о дожде:</b> {'🟢 Включены' if rain_alerts_enabled else '🔴 Отключены'}</blockquote>"""
                
                keyboard = [
                    [InlineKeyboardButton(
                        "🔴 Отключить ежедневные" if notifications_enabled else "🟢 Включить ежедневные",
                        callback_data='toggle_daily_notifications'
                    )],
                    [InlineKeyboardButton(
                        "🔴 Отключить дождь" if rain_alerts_enabled else "🟢 Включить дождь",
                        callback_data='toggle_rain_alerts'
                    )],
                    [InlineKeyboardButton("🕰 Изменить время уведомлений", callback_data='change_time')],
                    [InlineKeyboardButton("⚙️ Основные настройки", callback_data='main_settings'),
                     InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Check if the current message has media and handle accordingly
                if query.message.photo:
                    # If message has photo, edit caption instead of text
                    await query.edit_message_caption(caption=settings_text, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    # If message is text-only, edit text
                    await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error in settings handler: {e}")
                # Fallback message
                fallback_message = """🌤 <b>Настройки погоды</b>

❌ Произошла ошибка при загрузке настроек.

Выбери действие:"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data='settings')],
                    [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Check if the current message has media and handle accordingly
                if query.message.photo:
                    await query.edit_message_caption(caption=fallback_message, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await query.edit_message_text(fallback_message, reply_markup=reply_markup, parse_mode='HTML')
        
        elif query.data == 'notifications_menu':
            await self._show_notifications_menu(query, user_id)
        
        elif query.data == 'rain_settings':
            await self._show_rain_settings(query, user_id)
        
        elif query.data == 'change_time':
            await self._show_time_selection(query, 0)
        
        elif query.data == 'change_city':
            await self._show_city_selection(query, 0)
        
        elif query.data == 'settings_city':
            await self._show_city_selection(query, 0)
        
        elif query.data == 'settings_timezone':
            await self._show_timezone_selection(query, 0)
        
        
        elif query.data == 'toggle_daily_notifications':
            # Redirect to the correct handler
            await self._handle_toggle_daily_notifications(query, user_id)
        
        elif query.data == 'toggle_rain_alerts':
            # Redirect to the correct handler
            await self._handle_toggle_rain_alerts(query, user_id)
        
        elif query.data == 'check_rain_now':
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            
            # Get hourly forecast and check for rain
            hourly_forecast = weather_service.get_hourly_forecast(city, hours=6)
            if hourly_forecast:
                rain_info = weather_service.is_rain_expected(hourly_forecast, hours_ahead=3)
                
                if rain_info['rain_expected']:
                    time_str = rain_info['time'].split(' ')[1]
                    message = f"""🌧 **Проверка дождя для {city}**

{rain_info['message']}
⏰ Примерное время: **{time_str}**

🌂 Рекомендую взять зонт!"""
                else:
                    message = f"""☀️ **Проверка дождя для {city}**

В ближайшие часы дождь не ожидается.
Можешь не беспокоиться о зонте! 😊"""
            else:
                message = "❌ Не удалось получить прогноз погоды. Попробуй позже."
            
            keyboard = [
                [InlineKeyboardButton("🔄 Проверить ещё раз", callback_data='check_rain_now')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Handle pagination and selections
        elif query.data.startswith('city_page_'):
            page = int(query.data.split('_')[-1])
            await self._show_city_selection(query, page)
        
        elif query.data.startswith('select_city_'):
            city = query.data.split('select_city_')[1]
            await self._handle_city_selection(query, user_id, city)
        
        elif query.data == 'custom_city_input':
            await self._show_custom_city_input(query, user_id)
        
        elif query.data.startswith('timezone_page_'):
            page = int(query.data.split('_')[-1])
            await self._show_timezone_selection(query, page)
        
        elif query.data.startswith('select_timezone_'):
            timezone = query.data.split('select_timezone_')[1]
            await self._handle_timezone_selection(query, user_id, timezone)
        
        elif query.data.startswith('time_page_'):
            page = int(query.data.split('_')[-1])
            await self._show_time_selection(query, page)
        
        elif query.data.startswith('select_time_'):
            time_str = query.data.split('select_time_')[1]
            await self._handle_time_selection(query, user_id, time_str)
        
        elif query.data == 'custom_time_input':
            await self._show_custom_time_input(query, user_id)
        
        # Habit tracking handlers
        elif query.data == 'habits_menu':
            await self._show_habits_menu(query)
        
        elif query.data == 'view_habits':
            await self._show_user_habits(query, user_id, 0)
        
        elif query.data == 'create_habit':
            await self._show_habit_creation(query, user_id)
        
        elif query.data == 'habit_stats':
            await self._show_habit_stats(query, user_id)
        
        elif query.data == 'manage_habits':
            await self._show_habit_management(query, user_id, 0)
        
        elif query.data.startswith('habits_page_'):
            page = int(query.data.split('_')[-1])
            await self._show_user_habits(query, user_id, page)
        
        elif query.data.startswith('habit_details_'):
            habit_id = query.data.split('habit_details_')[1]
            await self._show_habit_details(query, user_id, habit_id)
        
        elif query.data.startswith('complete_habit_'):
            habit_id = query.data.split('complete_habit_')[1]
            await self._complete_habit(query, user_id, habit_id)
        
        elif query.data.startswith('edit_habit_'):
            habit_id = query.data.split('edit_habit_')[1]
            await self._edit_habit(query, user_id, habit_id)
        
        elif query.data.startswith('delete_habit_'):
            habit_id = query.data.split('delete_habit_')[1]
            await self._confirm_delete_habit(query, user_id, habit_id)
        
        elif query.data.startswith('confirm_delete_'):
            habit_id = query.data.split('confirm_delete_')[1]
            await self._delete_habit(query, user_id, habit_id)
        
        elif query.data.startswith('suggestions_page_'):
            page = int(query.data.split('_')[-1])
            await self._show_habit_suggestions(query, user_id, page)
        
        elif query.data.startswith('suggest_habit_'):
            habit_name = query.data.split('suggest_habit_')[1]
            await self._start_habit_creation_with_name(query, user_id, habit_name)
        
        elif query.data == 'custom_habit_input':
            await self._show_custom_habit_input(query, user_id)
        
        elif query.data.startswith('habit_time_page_'):
            page = int(query.data.split('_')[-1])
            await self._show_habit_time_selection(query, user_id, page)
        
        elif query.data.startswith('habit_time_'):
            time_str = query.data.split('habit_time_')[1]
            await self._set_habit_time(query, user_id, time_str)
        
        elif query.data.startswith('toggle_day_'):
            day = query.data.split('toggle_day_')[1]
            await self._toggle_habit_day(query, user_id, day)
        
        elif query.data == 'select_weekdays':
            await self._select_weekdays(query, user_id)
        
        elif query.data == 'select_all_days':
            await self._select_all_days(query, user_id)
        
        elif query.data == 'days_selection_done':
            await self._finalize_habit_creation(query, user_id)
        
        elif query.data.startswith('manage_page_'):
            page = int(query.data.split('_')[-1])
            await self._show_habit_management(query, user_id, page)
        
        elif query.data == 'skip_description':
            await self._skip_habit_description(query, user_id)
        
        elif query.data == 'test_notification':
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            weather_data = weather_service.get_current_weather(city)
            
            test_message = f"🔔 **Тестовое уведомление**\n\n{weather_service.format_weather_message(weather_data)}"
            await context.bot.send_message(chat_id=user_id, text=test_message, parse_mode='Markdown')
            await query.edit_message_text("✅ Тестовое уведомление отправлено!", parse_mode='Markdown')
        
        # News handlers
        elif query.data == 'news_menu':
            await self._show_news_menu(query)
        
        elif query.data.startswith('news_category_'):
            category = query.data.split('news_category_')[1]
            await self._show_news_category(query, category, 0)
        
        elif query.data.startswith('news_page_'):
            # Format: news_page_category_page
            parts = query.data.split('_')
            if len(parts) >= 4:
                category = parts[2]
                page = int(parts[3])
                
                # Special handling for latest news (main menu)
                if category == 'latest':
                    await self._show_news_menu_with_page(query, page)
                else:
                    await self._show_news_category(query, category, page)
        
        elif query.data.startswith('news_details_'):
            # Format: news_details_category_page_article_index
            parts = query.data.split('_')
            logger.info(f"News details callback: {query.data}, parts: {parts}")
            if len(parts) >= 5:
                category = parts[2]
                page = int(parts[3])
                article_index = int(parts[4])
                logger.info(f"Processing news details: category={category}, page={page}, article_index={article_index}")
                await self._show_news_details(query, category, page, article_index)
            else:
                logger.error(f"Invalid news_details format: {query.data}")
    
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
    
    async def send_habit_reminder(self, habit) -> None:
        """Send habit reminder to a user"""
        try:
            reminder_message = f"""🎯 **Напоминание о привычке!**

⏰ Время выполнить: **{habit.name}**

{habit.description if habit.description else "Не забудь позаботиться о себе!"}

Отметь выполнение, когда будешь готов! 💪"""
            
            keyboard = [
                [InlineKeyboardButton("✅ Выполнено!", callback_data=f'complete_habit_{habit.habit_id}')],
                [InlineKeyboardButton("📋 Мои привычки", callback_data='view_habits')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.application.bot.send_message(
                chat_id=habit.user_id,
                text=reminder_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info(f"Habit reminder sent to user {habit.user_id} for habit '{habit.name}'")
        except Exception as e:
            logger.error(f"Error sending habit reminder to user {habit.user_id}: {e}")
    
    async def _show_city_selection(self, query, page: int) -> None:
        """Show city selection with pagination"""
        keyboard, has_next = InteractiveSettings.create_city_keyboard(page)
        
        total_pages = InteractiveSettings.get_city_page_count()
        
        message = f"""🌍 **Выбор города**

Выбери город из списка российских городов или введи свой:

📄 Страница {page + 1} из {total_pages}"""
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _show_timezone_selection(self, query, page: int) -> None:
        """Show timezone selection with pagination"""
        keyboard, has_next = InteractiveSettings.create_timezone_keyboard(page)
        
        total_pages = InteractiveSettings.get_timezone_page_count()
        
        message = f"""🕰 **Выбор часового пояса**

Выбери часовой пояс для корректного времени уведомлений:

📄 Страница {page + 1} из {total_pages}"""
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _show_time_selection(self, query, page: int) -> None:
        """Show time selection with pagination"""
        keyboard, has_next = InteractiveSettings.create_time_keyboard(page)
        
        total_pages = InteractiveSettings.get_time_page_count()
        
        message = f"""⏰ <b>Выбор времени уведомлений</b>

Выбери время для ежедневных уведомлений о погоде:

📄 Страница {page + 1} из {total_pages}"""
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
    
    async def _handle_city_selection(self, query, user_id: int, city: str) -> None:
        """Handle city selection"""
        # Test if the city is valid by fetching weather
        weather_data = weather_service.get_current_weather(city)
        
        if weather_data:
            # Update user settings
            if user_id not in user_settings:
                user_settings[user_id] = {}
            user_settings[user_id]['city'] = weather_data['city']
            
            # Update rain monitoring with new city
            if user_settings[user_id].get('rain_alerts_enabled', True):
                rain_monitor.update_user_city(user_id, weather_data['city'])
            
            message = f"✅ Город изменен на **{weather_data['city']}, {weather_data['country']}**"
            
            keyboard = [
                [InlineKeyboardButton("🌤 Посмотреть погоду", callback_data='current_weather')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # City not found, show error and return to selection
            message = f"❌ Не удалось найти город '{city}'. Попробуй выбрать другой."
            
            keyboard = [
                [InlineKeyboardButton("🔙 К выбору городов", callback_data='city_page_0')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _handle_timezone_selection(self, query, user_id: int, timezone: str) -> None:
        """Handle timezone selection"""
        try:
            import pytz
            pytz.timezone(timezone)  # Validate timezone
            
            # Update user settings
            if user_id not in user_settings:
                user_settings[user_id] = {}
            user_settings[user_id]['timezone'] = timezone
            
            # Update scheduler if notifications are enabled
            if user_settings[user_id].get('notifications_enabled', False):
                scheduler.add_user(user_id, user_settings[user_id])
            
            timezone_name = InteractiveSettings.find_timezone_name(timezone)
            message = f"✅ Часовой пояс изменен на **{timezone_name}**"
            
            keyboard = [
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            message = f"❌ Ошибка при установке часового пояса. Попробуй ещё раз."
            
            keyboard = [
                [InlineKeyboardButton("🔙 К выбору часовых поясов", callback_data='timezone_page_0')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _handle_time_selection(self, query, user_id: int, time_str: str) -> None:
        """Handle time selection"""
        try:
            from datetime import datetime
            datetime.strptime(time_str, '%H:%M')  # Validate time format
            
            # Update database
            db.update_weather_settings(user_id, notification_time=time_str)
            
            # Update scheduler if notifications are enabled
            weather_settings = db.get_weather_settings(user_id)
            if weather_settings and weather_settings.get('daily_notifications_enabled', False):
                scheduler.update_user_time(user_id, time_str)
            
            message = f"✅ Время уведомлений изменено на <b>{time_str}</b>"
            
            keyboard = [
                [InlineKeyboardButton("⚙️ Настройки погоды", callback_data='settings')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in _handle_time_selection: {e}")
            message = f"❌ Ошибка при установке времени. Попробуй ещё раз."
            
            keyboard = [
                [InlineKeyboardButton("🔙 К выбору времени", callback_data='time_page_0')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    
    async def _show_custom_city_input(self, query, user_id: int) -> None:
        """Show custom city input instructions"""
        user_states[user_id] = 'waiting_city_input'
        
        message = """✏️ **Ввод своего города**

Напиши название города, который хочешь установить.

**Примеры:**
• `Москва`
• `Новосибирск`
• `London`
• `New York`

Просто отправь сообщение с названием города."""
        
        keyboard = InteractiveSettings.create_custom_input_keyboard('city')
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _show_custom_time_input(self, query, user_id: int) -> None:
        """Show custom time input instructions"""
        user_states[user_id] = 'waiting_time_input'
        
        message = """✏️ **Ввод своего времени**

Напиши время в формате ЧЧ:ММ для ежедневных уведомлений.

**Примеры:**
• `07:30`
• `08:00`
• `21:15`

Просто отправь сообщение с временем."""
        
        keyboard = InteractiveSettings.create_custom_input_keyboard('time')
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # Habit tracking methods
    async def _show_habits_menu(self, query) -> None:
        """Show main habits menu"""
        message = """🎯 **Трекер привычек**

Добро пожаловать в систему отслеживания привычек! Здесь ты можешь:

• Создавать новые привычки
• Отслеживать их выполнение
• Получать напоминания
• Просматривать статистику

Выбери действие:"""
        
        keyboard = HabitInterface.create_main_habits_menu()
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            # If message has photo, edit caption instead of text
            await query.edit_message_caption(caption=message, reply_markup=keyboard, parse_mode='Markdown')
        else:
            # If message is text-only, edit text
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _show_user_habits(self, query, user_id: int, page: int) -> None:
        """Show user's habits with pagination"""
        habits = db.get_user_habits(user_id)
        
        if not habits:
            message = """📋 **Мои привычки**

У тебя пока нет привычек для отслеживания.

Создай свою первую привычку, чтобы начать путь к лучшей версии себя! 🚀"""
            
            keyboard = [
                [InlineKeyboardButton("➕ Создать привычку", callback_data='create_habit')],
                [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            total_pages = HabitInterface.get_page_count(len(habits))
            message = f"""📋 **Мои привычки** (стр. {page + 1}/{total_pages})

{self._format_habit_list(habits[page*3:(page+1)*3])}

Нажми ✅ **Готово** чтобы отметить выполнение привычки."""
            
            keyboard, has_next = HabitInterface.create_habits_list_keyboard(habits, page)
            reply_markup = keyboard
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            # If message has photo, edit caption instead of text
            await query.edit_message_caption(caption=message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # If message is text-only, edit text
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_habit_details(self, query, user_id: int, habit_id: str) -> None:
        """Show detailed view of a habit"""
        habit = db.get_habit(habit_id)
        
        if not habit or habit.user_id != user_id:
            await query.edit_message_text(
                "❌ Привычка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
                ])
            )
            return
        
        message = HabitInterface.format_habit_details(habit)
        keyboard = HabitInterface.create_habit_details_keyboard(habit)
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            # If message has photo, edit caption instead of text
            await query.edit_message_caption(caption=message, reply_markup=keyboard, parse_mode='Markdown')
        else:
            # If message is text-only, edit text
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _complete_habit(self, query, user_id: int, habit_id: str) -> None:
        """Mark habit as completed"""
        success = db.mark_habit_completed(habit_id, user_id)
        
        if success:
            habit = db.get_habit(habit_id)
            completions = db.get_habit_completions(habit_id, 30)
            streak = self._calculate_streak(completions)
            
            if streak > 1:
                message = f"🎉 **Отлично!** Привычка '{habit['name']}' выполнена!\n\n🔥 Твоя серия: {streak} дней подряд! Так держать!"
            else:
                message = f"✅ **Готово!** Привычка '{habit['name']}' отмечена как выполненная!"
            
            keyboard = [
                [InlineKeyboardButton("📋 К списку привычек", callback_data='view_habits')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            message = "❌ Не удалось отметить привычку. Возможно, она уже выполнена сегодня."
            keyboard = [
                [InlineKeyboardButton("🔙 К привычкам", callback_data='view_habits')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            # If message has photo, edit caption instead of text
            await query.edit_message_caption(caption=message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # If message is text-only, edit text
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_habit_stats(self, query, user_id: int) -> None:
        """Show habit statistics"""
        message = self._get_stats_message(user_id)
        
        keyboard = [
            [InlineKeyboardButton("📋 Мои привычки", callback_data='view_habits')],
            [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            # If message has photo, edit caption instead of text
            await query.edit_message_caption(caption=message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # If message is text-only, edit text
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Additional habit methods (calling external module to keep file manageable)
    async def _show_habit_creation(self, query, user_id: int) -> None:
        await habit_methods.show_habit_creation(query, user_id, habit_creation_data, user_states, habit_tracker)
    
    async def _show_habit_suggestions(self, query, user_id: int, page: int) -> None:
        await habit_methods.show_habit_suggestions(query, user_id, page)
    
    async def _start_habit_creation_with_name(self, query, user_id: int, habit_name: str) -> None:
        await habit_methods.start_habit_creation_with_name(query, user_id, habit_name, habit_creation_data)
    
    async def _show_custom_habit_input(self, query, user_id: int) -> None:
        await habit_methods.show_custom_habit_input(query, user_id, user_states)
    
    async def _process_custom_habit_name(self, update, user_id: int, habit_name: str) -> None:
        await habit_methods.process_custom_habit_name(update, user_id, habit_name, habit_creation_data, user_states)
    
    async def _process_habit_description(self, update, user_id: int, description: str) -> None:
        await habit_methods.process_habit_description(update, user_id, description, habit_creation_data, user_states)
    
    async def _show_habit_time_selection(self, query, user_id: int, page: int) -> None:
        await habit_methods.show_habit_time_selection(query, user_id, page, habit_creation_data)
    
    async def _set_habit_time(self, query, user_id: int, time_str: str) -> None:
        await habit_methods.set_habit_time(query, user_id, time_str, habit_creation_data)
    
    async def _toggle_habit_day(self, query, user_id: int, day: str) -> None:
        await habit_methods.toggle_habit_day(query, user_id, day, habit_creation_data)
    
    async def _select_weekdays(self, query, user_id: int) -> None:
        await habit_methods.select_weekdays(query, user_id, habit_creation_data)
    
    async def _select_all_days(self, query, user_id: int) -> None:
        await habit_methods.select_all_days(query, user_id, habit_creation_data)
    
    async def _finalize_habit_creation(self, query, user_id: int) -> None:
        await habit_methods.finalize_habit_creation(query, user_id, habit_creation_data, db)
    
    async def _show_habit_management(self, query, user_id: int, page: int) -> None:
        await habit_methods.show_habit_management(query, user_id, page, db)
    
    async def _confirm_delete_habit(self, query, user_id: int, habit_id: str) -> None:
        await habit_methods.confirm_delete_habit(query, user_id, habit_id, db)
    
    async def _delete_habit(self, query, user_id: int, habit_id: str) -> None:
        await habit_methods.delete_habit(query, user_id, habit_id, db)
    
    async def _edit_habit(self, query, user_id: int, habit_id: str) -> None:
        await habit_methods.edit_habit(query, user_id, habit_id)
    
    async def _skip_habit_description(self, query, user_id: int) -> None:
        """Skip habit description and proceed to time selection"""
        if user_id in habit_creation_data:
            # Set empty description
            habit_creation_data[user_id]['description'] = ''
            
            # Proceed to time selection
            await self._show_habit_time_selection(query, user_id, 0)
        else:
            # If no habit creation data, go back to habit creation
            await self._show_habit_creation(query, user_id)
    
    # Helper methods for habit formatting and calculations
    def _format_habit_list(self, habits: List[Dict]) -> str:
        """Format a list of habits for display"""
        if not habits:
            return "У тебя пока нет активных привычек."
        
        message = ""
        
        for habit in habits:
            status = "✅" if db.is_habit_completed_today(habit['habit_id']) else "⏳"
            completions = db.get_habit_completions(habit['habit_id'], 30)
            streak = self._calculate_streak(completions)
            streak_text = f" • Серия: {streak} дн." if streak > 0 else ""
            
            message += f"{status} **{habit['name']}**{streak_text}\n"
            if habit['description']:
                message += f"   _{habit['description']}_\n"
            message += f"   ⏰ {habit['reminder_time']} • Дни: {len(habit['reminder_days'])}/7\n\n"
        
        return message
    
    def _calculate_streak(self, completions: List[str]) -> int:
        """Calculate current completion streak"""
        if not completions:
            return 0
        
        from datetime import datetime, timedelta
        
        # Sort completions and calculate streak from today backwards
        sorted_completions = sorted(completions, reverse=True)
        today = datetime.now()
        streak = 0
        
        for i, completion_date in enumerate(sorted_completions):
            expected_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if completion_date == expected_date:
                streak += 1
            else:
                break
        
        return streak
    
    def _get_stats_message(self, user_id: int) -> str:
        """Get statistics message for user"""
        habits = db.get_user_habits(user_id)
        
        if not habits:
            return "📊 **Статистика привычек**\n\nУ тебя пока нет привычек для отслеживания."
        
        total_habits = len(habits)
        completed_today = sum(1 for h in habits if db.is_habit_completed_today(h['habit_id']))
        
        # Calculate total streak and average completion
        total_streak = 0
        total_completion_rate = 0
        
        for habit in habits:
            completions = db.get_habit_completions(habit['habit_id'], 7)  # Last 7 days
            streak = self._calculate_streak(db.get_habit_completions(habit['habit_id'], 30))
            total_streak += streak
            
            # Calculate completion rate for last week
            expected_days = len(habit['reminder_days'])  # Assume all days for simplicity
            completed_days = len([c for c in completions if c >= (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")])
            completion_rate = (completed_days / min(expected_days, 7) * 100) if expected_days > 0 else 0
            total_completion_rate += completion_rate
        
        avg_completion = total_completion_rate / total_habits if total_habits > 0 else 0
        
        message = f"""📊 **Статистика привычек**

📈 **Сегодня:** {completed_today}/{total_habits} выполнено
🔥 **Общая серия:** {total_streak} дней
📅 **За неделю:** {avg_completion:.1f}% выполнение
🎯 **Всего привычек:** {total_habits}

"""
        
        # Show top performing habit
        if habits:
            best_habit = None
            best_streak = 0
            
            for habit in habits:
                completions = db.get_habit_completions(habit['habit_id'], 30)
                streak = self._calculate_streak(completions)
                if streak > best_streak:
                    best_streak = streak
                    best_habit = habit
            
            if best_habit and best_streak > 0:
                message += f"🏆 **Лучшая серия:** {best_habit['name']} ({best_streak} дн.)"
        
        return message
    
    async def _show_main_menu(self, query) -> None:
        """Show the main menu"""
        user_name = query.from_user.first_name
        welcome_message = f"""👋 Привет, {user_name}! Я Тео, твой персональный помощник!

🌤 Получай актуальную информацию о погоде
🎯 Отслеживай свои привычки и достигай целей
ℹ️ Узнай, как пользоваться всеми функциями

Выбери нужный раздел:"""
        
        keyboard = [
            [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
            [InlineKeyboardButton("🎯 Привычки", callback_data='habits_menu')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='main_settings')],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_main_settings(self, query, user_id: int) -> None:
        """Show main settings menu with city and timezone"""
        weather_settings = db.get_weather_settings(user_id)
        
        if weather_settings:
            city = weather_settings.get('city', DEFAULT_CITY)
            timezone = weather_settings.get('timezone', TIMEZONE)
        else:
            city = DEFAULT_CITY
            timezone = TIMEZONE
        
        settings_text = f"""⚙️ **Основные настройки**

**Город:** {city}
**Часовой пояс:** {timezone}

Эти настройки используются для всех уведомлений в боте:
• Погодные уведомления
• Уведомления о дожде
• Напоминания о привычках
• Все временные расчеты"""
        
        keyboard = [
            [InlineKeyboardButton("🌍 Изменить город", callback_data='settings_city')],
            [InlineKeyboardButton("🕰 Изменить часовой пояс", callback_data='settings_timezone')],
            [InlineKeyboardButton("🌤 Настройки погоды", callback_data='settings')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            # If message has photo, edit caption instead of text
            await query.edit_message_caption(caption=settings_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            # If message is text-only, edit text
            await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def _show_weather_menu(self, query, user_id: int) -> None:
        """Show the weather menu with current weather, forecast, and notification status"""
        try:
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            
            # Get current weather
            current_weather = weather_service.get_current_weather(city)
            current_weather_text = ""
            if current_weather:
                temp = current_weather.get('temperature', 'N/A')
                description = current_weather.get('description', 'N/A')
                humidity = current_weather.get('humidity', 'N/A')
                wind_speed = current_weather.get('wind_speed', 'N/A')
                current_weather_text = f"""🌤 <b>Текущая погода в {city}:</b>
<blockquote>🌡 Температура: {temp}°C    
☁️ {description}
💧 Влажность: {humidity}%
💨 Ветер: {wind_speed} м/с</blockquote>"""
            else:
                current_weather_text = f"❌ Не удалось получить погоду для {city}"
            
            # Get 3-hour forecast for next consecutive hours
            from datetime import datetime
            now = datetime.now()
            current_hour = now.hour
            
            # Calculate next 3 consecutive hours
            next_hours = []
            for i in range(1, 4):  # Next 1, 2, 3 hours
                next_hour = current_hour + i
                if next_hour >= 24:
                    next_hour -= 24
                next_hours.append(next_hour)
            
            # Get hourly forecast data
            hourly_forecast = weather_service.get_hourly_forecast(city, hours=12)
            forecast_text = ""
            if hourly_forecast and hourly_forecast.get('forecasts'):
                forecast_text = "\n\n⏰ <b>Прогноз осадков на 3 часа:</b>"
                forecast_items = []
                
                for target_hour in next_hours:
                    # Find the closest available forecast for this hour
                    closest_forecast = None
                    min_hour_diff = 24
                    
                    for forecast in hourly_forecast.get('forecasts', []):
                        forecast_time = datetime.fromisoformat(forecast['datetime'].replace('Z', '+00:00'))
                        forecast_hour = forecast_time.hour
                        
                        # Calculate hour difference (considering 24-hour cycle)
                        hour_diff = abs(forecast_hour - target_hour)
                        if hour_diff > 12:  # Handle day boundary
                            hour_diff = 24 - hour_diff
                        
                        if hour_diff < min_hour_diff:
                            min_hour_diff = hour_diff
                            closest_forecast = forecast
                    
                    if closest_forecast:
                        time_str = f"{target_hour:02d}:00"
                        description = closest_forecast.get('description', '')
                        rain_prob = closest_forecast.get('rain_probability', 0)
                        weather_id = closest_forecast.get('weather_id', 0)
                        
                        # Check if precipitation is expected (weather ID or high probability)
                        is_rain = (200 <= weather_id <= 599) or rain_prob > 50  # Thunderstorm, Drizzle, Rain
                        
                        if is_rain:
                            prob_text = f" ({rain_prob:.0f}%)" if rain_prob > 0 else ""
                            forecast_items.append(f"• {time_str}: 🌧 {description}{prob_text}")
                        else:
                            forecast_items.append(f"• {time_str}: ☀️ Без осадков")
                    else:
                        # Fallback if no forecast found
                        time_str = f"{target_hour:02d}:00"
                        forecast_items.append(f"• {time_str}: ☀️ Без осадков")
                
                forecast_text += f"\n<blockquote>{chr(10).join(forecast_items)}</blockquote>"
            else:
                forecast_text = "\n\n❌ Не удалось получить прогноз осадков"
            
            # Get notification status
            notifications_enabled = weather_settings.get('daily_notifications_enabled', False) if weather_settings else False
            rain_alerts_enabled = weather_settings.get('rain_alerts_enabled', True) if weather_settings else True
            notification_time = weather_settings.get('notification_time', '08:00') if weather_settings else '08:00'
            
            notification_status = f"""🔔 <b>Статус уведомлений:</b>
<blockquote>• Ежедневные: {'🟢 Включены' if notifications_enabled else '🔴 Отключены'} ({notification_time})
• Дождь: {'🟢 Включены' if rain_alerts_enabled else '🔴 Отключены'}</blockquote>"""
            
            # Add timestamp to make each update unique
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            message = f"""{current_weather_text}{forecast_text}

{notification_status}

⏰ <i>Обновлено: {timestamp}</i>

Выбери действие:"""
            
            # Ensure message is not empty
            if not message.strip():
                message = f"""🌤 <b>Погода в {city}</b>

❌ Не удалось получить данные о погоде. Попробуй обновить.

Выбери действие:"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data='weather_menu_refresh')],
                [InlineKeyboardButton("📅 Прогноз на 3 дня", callback_data='forecast')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                # Use custom weather avatar image
                with open('bot_avatar_for_weather.jpg', 'rb') as photo:
                    await query.edit_message_media(
                        media=InputMediaPhoto(
                            media=photo,
                            caption=message,
                            parse_mode='HTML'
                        ),
                        reply_markup=reply_markup
                    )
            except FileNotFoundError:
                # Fallback to text message if image file not found
                logger.warning("Weather avatar image not found, using text message")
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
            except Exception as e:
                # Fallback to text message if error
                logger.error(f"Error displaying weather avatar: {e}")
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in _show_weather_menu: {e}")
            # Fallback message
            fallback_message = f"""🌤 <b>Погода</b>

❌ Произошла ошибка при получении данных о погоде.

Выбери действие:"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data='weather_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                # Try to use weather avatar for fallback too
                with open('bot_avatar_for_weather.jpg', 'rb') as photo:
                    await query.edit_message_media(
                        media=InputMediaPhoto(
                            media=photo,
                            caption=fallback_message,
                            parse_mode='HTML'
                        ),
                        reply_markup=reply_markup
                    )
            except:
                # Final fallback to text message
                await query.edit_message_text(fallback_message, reply_markup=reply_markup, parse_mode='HTML')
    
    async def _show_forecast(self, query, user_id: int) -> None:
        """Show 3-day weather forecast"""
        try:
            weather_settings = db.get_weather_settings(user_id)
            city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            forecast_data = weather_service.get_weather_forecast(city)
            message = weather_service.format_forecast_message(forecast_data)
            
            # Add timestamp to make each update unique
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            message += f"⏰ <i>Обновлено: {timestamp}</i>"
            
            # Simplified keyboard with only 3 buttons
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить прогноз", callback_data='forecast_refresh')],
                [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Check if the current message has media and handle accordingly
            if query.message.photo:
                # If message has photo, edit caption instead of text
                await query.edit_message_caption(caption=message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                # If message is text-only, edit text
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error in _show_forecast: {e}")
            # Fallback message
            fallback_message = f"""📅 <b>Прогноз погоды</b>

❌ Произошла ошибка при получении прогноза погоды.

Выбери действие:"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data='forecast_refresh')],
                [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Check if the current message has media and handle accordingly
            if query.message.photo:
                await query.edit_message_caption(caption=fallback_message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await query.edit_message_text(fallback_message, reply_markup=reply_markup, parse_mode='HTML')
    
    async def _show_rain_settings(self, query, user_id: int) -> None:
        """Show rain alert settings"""
        weather_settings = db.get_weather_settings(user_id)
        rain_alerts_enabled = weather_settings.get('rain_alerts_enabled', True) if weather_settings else True
        city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
        
        status = "🟢 Включены" if rain_alerts_enabled else "🔴 Отключены"
        
        message = f"""☔ **Уведомления о дожде**

**Текущий статус:** {status}
**Город:** {city}

Я буду предупреждать тебя за час до дождя, чтобы ты не забыл взять зонт! 🌂

Уведомления основаны на прогнозе погоды для твоего города."""
        
        keyboard = [
            [InlineKeyboardButton(
                "🔴 Отключить" if rain_alerts_enabled else "🟢 Включить",
                callback_data='toggle_rain_alerts'
            )],
            [InlineKeyboardButton("🌧 Проверить дождь сейчас", callback_data='check_rain_now')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings'),
             InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_help_message(self, update_or_query) -> None:
        """Show comprehensive help message"""
        try:
            help_text = """📖 **Инструкция по использованию Тео**

**🌤 ПОГОДА**
• Получай актуальную погоду и прогнозы
• Устанавливай свой город через настройки
• Получай уведомления о дожде за час до осадков
• Настраивай ежедневные уведомления о погоде

**📰 НОВОСТИ**
• Последние новости России
• Главные новости по популярности
• Спортивные новости
• Экономика и бизнес
• Технологии и наука

**🎯 ПРИВЫЧКИ**
• Создавай полезные привычки
• Получай напоминания в удобное время
• Отслеживай серии выполнения
• Просматривай статистику прогресса

**⚙️ КАК ПОЛЬЗОВАТЬСЯ:**

1️⃣ **Навигация:** Используй кнопки для перемещения по меню
2️⃣ **Погода:** Нажми "🌤 Погода" → увидишь текущую погоду и прогноз осадков на 3 часа
3️⃣ **Новости:** Нажми "📰 Новости" → выбери категорию и читай актуальные новости
4️⃣ **Привычки:** Нажми "🎯 Привычки" → создавай и отслеживай
5️⃣ **Настройки:** Нажми "⚙️ Настройки" → управляй городом, часовым поясом и уведомлениями

**💡 СОВЕТЫ:**
• Установи свой город в настройках для точной погоды
• Создай привычки с напоминаниями для лучших результатов
• Используй кнопку "✅ Готово" для быстрого отмечания привычек
• Включи уведомления о дожде, чтобы не забыть зонт
• Читай новости для информированности

**❓ ПОДДЕРЖКА:**
Если что-то не работает или нужна помощь, просто напиши сообщение!"""
            
            keyboard = [
                [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu'),
                 InlineKeyboardButton("📰 Новости", callback_data='news_menu')],
                [InlineKeyboardButton("🎯 Привычки", callback_data='habits_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Handle both message and callback query
            if hasattr(update_or_query, 'edit_message_text'):
                # It's a callback query
                # Check if the current message has media and handle accordingly
                if update_or_query.message.photo:
                    # If message has photo, edit caption instead of text
                    await update_or_query.edit_message_caption(caption=help_text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    # If message is text-only, edit text
                    await update_or_query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                # It's a message
                await update_or_query.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in _show_help_message: {e}")
            # Fallback message
            fallback_text = """📖 **Помощь**

❌ Произошла ошибка при загрузке справки.

[🏠 Главное меню](callback_data='main_menu')"""
            
            keyboard = [
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if hasattr(update_or_query, 'edit_message_text'):
                # Check if the current message has media and handle accordingly
                if update_or_query.message.photo:
                    # If message has photo, edit caption instead of text
                    await update_or_query.edit_message_caption(caption=fallback_text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    # If message is text-only, edit text
                    await update_or_query.edit_message_text(fallback_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update_or_query.reply_text(fallback_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_notifications_menu(self, query, user_id: int) -> None:
        """Show the notifications menu"""
        weather_settings = db.get_weather_settings(user_id)
        
        if weather_settings:
            notifications_enabled = weather_settings.get('daily_notifications_enabled', False)
            notification_time = weather_settings.get('notification_time', '08:00')
            city = weather_settings.get('city', DEFAULT_CITY)
            timezone = weather_settings.get('timezone', TIMEZONE)
        else:
            notifications_enabled = False
            notification_time = '08:00'
            city = DEFAULT_CITY
            timezone = TIMEZONE
        
        status = "🟢 Включены" if notifications_enabled else "🔴 Отключены"
        
        message = f"""📋 **Настройки уведомлений**

**Статус:** {status}
**Время:** {notification_time}
**Город:** {city}
**Часовой пояс:** {timezone}

Используй кнопки ниже для управления уведомлениями:"""
        
        keyboard = [
            [InlineKeyboardButton(
                "🔴 Отключить" if notifications_enabled else "🟢 Включить",
                callback_data='toggle_daily_notifications'
            )],
            [InlineKeyboardButton("⏰ Изменить время", callback_data='change_time'),
             InlineKeyboardButton("🌍 Изменить город", callback_data='settings_city')],
            [InlineKeyboardButton("🔄 Тестовое уведомление", callback_data='test_notification')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings'),
             InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
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
    
    # News methods
    async def _show_news_menu(self, query) -> None:
        """Show news menu with latest news and specific category buttons"""
        # Get user timezone from database
        user_id = query.from_user.id
        weather_settings = db.get_weather_settings(user_id)
        user_timezone = weather_settings.get('timezone', 'UTC') if weather_settings else 'UTC'
        
        # Debug logging
        logger.info(f"User {user_id} timezone: {user_timezone}")
        logger.info(f"Weather settings: {weather_settings}")
        
        # Get latest news data with user timezone
        latest_news = news_service.get_news("latest", user_timezone)
        
        if not latest_news:
            message = """❌ Извини, не удалось получить новости. Попробуй позже.

Выбери категорию новостей:"""
            keyboard = NewsInterface.create_news_main_menu(page=0, total_pages=1)
            
            # Send with news avatar image
            try:
                with open('bot_avatar_for_news.jpeg', 'rb') as photo:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=photo, caption=message, parse_mode='HTML'),
                        reply_markup=keyboard
                    )
            except Exception as e:
                logger.error(f"Error sending news menu with image: {e}")
                # Fallback to text-only
                await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
            return
        
        # Format latest news section in new format with Telegram quotes
        news_section = ""
        if latest_news.get('articles'):
            news_section = "⚡ <b>Последние новости</b>⚡\n\n"
            for i, article in enumerate(latest_news['articles'][:5], 1):
                title = article.get('title', '')
                time = article.get('time', '')
                if title:
                    news_section += f"<blockquote>{i}. {title} • {time}</blockquote>\n\n"
            news_section += "💡 <i>Ты можете ознакомиться с новостями подробнее, воспользовавшись кнопками 1-5, или выбрать интересующую категорию.</i>"
        
        message = f"""{news_section}"""
        
        # Calculate total pages for latest news
        total_pages = NewsInterface.get_page_count(len(latest_news['articles'])) if latest_news.get('articles') else 1
        
        keyboard = NewsInterface.create_news_main_menu(page=0, total_pages=total_pages)
        
        # Send with news avatar image
        try:
            with open('bot_avatar_for_news.jpeg', 'rb') as photo:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=photo, caption=message, parse_mode='HTML'),
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error sending news menu with image: {e}")
            # Fallback to text-only
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
    
    async def _show_news_menu_with_page(self, query, page: int = 0) -> None:
        """Show news menu with specific page for latest news"""
        # Get user timezone from database
        user_id = query.from_user.id
        weather_settings = db.get_weather_settings(user_id)
        user_timezone = weather_settings.get('timezone', 'UTC') if weather_settings else 'UTC'
        
        # Get latest news data with user timezone
        latest_news = news_service.get_news("latest", user_timezone)
        
        if not latest_news:
            message = """❌ Извини, не удалось получить новости. Попробуй позже.

Выбери категорию новостей:"""
            keyboard = NewsInterface.create_news_main_menu(page=page, total_pages=1)
            
            # Send with news avatar image
            try:
                with open('bot_avatar_for_news.jpeg', 'rb') as photo:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=photo, caption=message, parse_mode='HTML'),
                        reply_markup=keyboard
                    )
            except Exception as e:
                logger.error(f"Error sending news menu with image: {e}")
                # Fallback to text-only
                await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
            return
        
        # Format latest news section for specific page
        news_section = ""
        if latest_news.get('articles'):
            # Calculate articles for current page
            articles_per_page = 5
            start_idx = page * articles_per_page
            end_idx = start_idx + articles_per_page
            page_articles = latest_news['articles'][start_idx:end_idx]
            
            news_section = "⚡ <b>Последние новости</b>⚡\n\n"
            for i, article in enumerate(page_articles, start=start_idx + 1):
                title = article.get('title', '')
                time = article.get('time', '')
                if title:
                    news_section += f"<blockquote>{i}. {title} • {time}</blockquote>\n\n"
            news_section += "💡 <i>Ты можешь ознакомиться с новостями подробнее, воспользовавшись кнопками 1-5, или выбрать интересующую категорию.</i>"
        
        message = f"""{news_section}"""
        
        # Calculate total pages for latest news
        total_pages = NewsInterface.get_page_count(len(latest_news['articles'])) if latest_news.get('articles') else 1
        
        keyboard = NewsInterface.create_news_main_menu(page=page, total_pages=total_pages)
        
        # Send with news avatar image
        try:
            with open('bot_avatar_for_news.jpeg', 'rb') as photo:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=photo, caption=message, parse_mode='HTML'),
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error sending news menu with image: {e}")
            # Fallback to text-only
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
    
    async def _show_news_category(self, query, category: str, page: int = 0) -> None:
        """Show news for a specific category"""
        # Get user timezone from database
        user_id = query.from_user.id
        weather_settings = db.get_weather_settings(user_id)
        user_timezone = weather_settings.get('timezone', 'UTC') if weather_settings else 'UTC'
        
        # Get news data with user timezone
        news_data = news_service.get_news(category, user_timezone)
        
        if not news_data:
            message = "❌ Извини, не удалось получить новости. Попробуй позже."
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f'news_category_{category}')],
                [InlineKeyboardButton("📰 К меню новостей", callback_data='news_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send with news avatar image
            try:
                with open('bot_avatar_for_news.jpeg', 'rb') as photo:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=photo, caption=message, parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Error sending news category error with image: {e}")
                # Fallback to text-only
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        # Format news section in the same format as main news menu
        news_section = ""
        if news_data.get('articles'):
            # Get category emoji and name
            category_emoji = news_data.get('category_emoji', '📰')
            category_name = news_data.get('category_name', 'Новости')
            
            news_section = f"⚡ <b>{category_name}</b>⚡\n\n"
            
            # Show articles for current page
            articles_per_page = 5
            start_idx = page * articles_per_page
            end_idx = start_idx + articles_per_page
            page_articles = news_data['articles'][start_idx:end_idx]
            
            for i, article in enumerate(page_articles, start=start_idx + 1):
                title = article.get('title', '')
                time = article.get('time', '')
                if title:
                    news_section += f"<blockquote>{i}. {title} • {time}</blockquote>\n\n"
            
            # Add description
            total_pages = NewsInterface.get_page_count(len(news_data['articles']))
            if total_pages > 1:
                news_section += f"💡 <i>Ты можешь ознакомиться с новостями подробнее, воспользовавшись кнопками 1-5, или перейти на другую страницу. Страница {page + 1} из {total_pages}.</i>"
            else:
                news_section += "💡 <i>Ты можешь ознакомиться с новостями подробнее, воспользовавшись кнопками 1-5.</i>"
        
        message = f"""{news_section}"""
        
        # Create navigation keyboard
        total_pages = NewsInterface.get_page_count(len(news_data['articles']))
        keyboard = NewsInterface.create_news_navigation_keyboard(category, page, total_pages)
        
        # Send with news avatar image
        try:
            with open('bot_avatar_for_news.jpeg', 'rb') as photo:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=photo, caption=message, parse_mode='HTML'),
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error sending news category with image: {e}")
            # Fallback to text-only
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
    
    async def _show_news_details(self, query, category: str, page: int, article_index: int) -> None:
        """Show detailed news article"""
        # Get user timezone from database
        user_id = query.from_user.id
        weather_settings = db.get_weather_settings(user_id)
        user_timezone = weather_settings.get('timezone', 'UTC') if weather_settings else 'UTC'
        
        # Get news data with user timezone
        news_data = news_service.get_news(category, user_timezone)
        
        if not news_data:
            message = "❌ Извини, не удалось получить новости."
            keyboard = [
                [InlineKeyboardButton("🔙 К списку новостей", callback_data=f'news_page_{category}_{page}')],
                [InlineKeyboardButton("📰 К меню новостей", callback_data='news_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Check if the current message has media and handle accordingly
            if query.message.photo:
                await query.edit_message_caption(caption=message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        # Calculate correct article index (article_index is now the real article number)
        # Convert from real article number to array index
        array_index = article_index - 1  # Convert from 1-based to 0-based
        
        # Format news details (use array_index + 1 for 1-based indexing)
        message = news_service.format_news_details(news_data, array_index + 1)
        
        # Create details keyboard
        keyboard = NewsInterface.create_news_details_keyboard(category, page, article_index)
        
        # Get article image URL
        article = news_data['articles'][array_index]
        image_url = article.get('image_url', '')
        
        # Try to use article image, fallback to news avatar
        if image_url:
            try:
                # Download and use article image
                import requests
                from io import BytesIO
                
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    image_data = BytesIO(response.content)
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=image_data, caption=message, parse_mode='HTML'),
                        reply_markup=keyboard
                    )
                    return
            except Exception as e:
                logger.error(f"Error downloading article image: {e}")
        
        # Fallback to news avatar image
        try:
            with open('bot_avatar_for_news.jpeg', 'rb') as photo:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=photo, caption=message, parse_mode='HTML'),
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error sending news details with image: {e}")
            # Fallback to text-only
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
    
    async def _handle_toggle_daily_notifications(self, query, user_id: int) -> None:
        """Handle toggle daily notifications"""
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
        
        # Immediately refresh the settings interface to show updated state
        await self._refresh_weather_settings(query, user_id)
    
    async def _handle_toggle_rain_alerts(self, query, user_id: int) -> None:
        """Handle toggle rain alerts"""
        weather_settings = db.get_weather_settings(user_id)
        current_status = weather_settings.get('rain_alerts_enabled', True) if weather_settings else True
        new_status = not current_status
        
        # Update in database
        db.update_weather_settings(user_id, rain_alerts_enabled=new_status)
        
        if new_status:
            # Enable rain alerts
            updated_settings = db.get_weather_settings(user_id)
            rain_monitor.enable_rain_alerts(user_id, updated_settings)
        else:
            # Disable rain alerts
            rain_monitor.disable_rain_alerts(user_id)
        
        # Immediately refresh the settings interface to show updated state
        await self._refresh_weather_settings(query, user_id)
    
    async def _refresh_weather_settings(self, query, user_id: int) -> None:
        """Refresh weather settings interface with updated data"""
        try:
            weather_settings = db.get_weather_settings(user_id)
            
            if weather_settings:
                city = weather_settings.get('city', DEFAULT_CITY)
                notifications_enabled = weather_settings.get('daily_notifications_enabled', False)
                notification_time = weather_settings.get('notification_time', '08:00')
                rain_alerts_enabled = weather_settings.get('rain_alerts_enabled', True)
            else:
                city = DEFAULT_CITY
                notifications_enabled = False
                notification_time = '08:00'
                rain_alerts_enabled = True
            
            settings_text = f"""🌤 <b>Настройки погоды</b>

<blockquote><b>Город:</b> {city}
<b>Ежедневные уведомления:</b> {'🟢 Включены' if notifications_enabled else '🔴 Отключены'} ({notification_time})
<b>Уведомления о дожде:</b> {'🟢 Включены' if rain_alerts_enabled else '🔴 Отключены'}</blockquote>"""
            
            keyboard = [
                [InlineKeyboardButton(
                    "🔴 Отключить ежедневные" if notifications_enabled else "🟢 Включить ежедневные",
                    callback_data='toggle_daily_notifications'
                )],
                [InlineKeyboardButton(
                    "🔴 Отключить дождь" if rain_alerts_enabled else "🟢 Включить дождь",
                    callback_data='toggle_rain_alerts'
                )],
                [InlineKeyboardButton("🕰 Изменить время уведомлений", callback_data='change_time')],
                [InlineKeyboardButton("⚙️ Основные настройки", callback_data='main_settings'),
                 InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Check if the current message has media and handle accordingly
            if query.message.photo:
                # If message has photo, edit caption instead of text
                await query.edit_message_caption(caption=settings_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                # If message is text-only, edit text
                await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error in _refresh_weather_settings: {e}")
            # Fallback message
            fallback_message = """🌤 <b>Настройки погоды</b>

❌ Произошла ошибка при обновлении настроек.

Выбери действие:"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data='settings')],
                [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Check if the current message has media and handle accordingly
            if query.message.photo:
                await query.edit_message_caption(caption=fallback_message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await query.edit_message_text(fallback_message, reply_markup=reply_markup, parse_mode='HTML')
    

    
    async def _show_main_menu(self, query) -> None:
        """Show main menu with bot avatar"""
        try:
            message = """🏠 **Главное меню**

Добро пожаловать в Тео! Выбери нужную функцию:"""
            
            keyboard = [
                [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                [InlineKeyboardButton("📰 Новости", callback_data='news_menu')],
                [InlineKeyboardButton("🎯 Привычки", callback_data='habits_menu')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='main_settings')],
                [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                # Use custom bot avatar image
                with open('bot_avatar.jpg', 'rb') as photo:
                    await query.edit_message_media(
                        media=InputMediaPhoto(
                            media=photo,
                            caption=message,
                            parse_mode='Markdown'
                        ),
                        reply_markup=reply_markup
                    )
            except FileNotFoundError:
                # Fallback to text message if image file not found
                logger.warning("Bot avatar image not found, using text message")
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as e:
                # Fallback to text message if error
                logger.error(f"Error displaying bot avatar: {e}")
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in _show_main_menu: {e}")
            # Fallback message
            fallback_message = """🏠 **Главное меню**

Добро пожаловать в Тео! Выбери нужную функцию:"""
            
            keyboard = [
                [InlineKeyboardButton("🌤 Погода", callback_data='weather_menu')],
                [InlineKeyboardButton("📰 Новости", callback_data='news_menu')],
                [InlineKeyboardButton("🎯 Привычки", callback_data='habits_menu')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='main_settings')],
                [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(fallback_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    def run(self) -> None:
        """Start the bot"""
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("weather", self.weather_command))
        self.application.add_handler(CommandHandler("forecast", self.forecast_command))
        self.application.add_handler(CommandHandler("setcity", self.setcity_command))
        self.application.add_handler(CommandHandler("notifications", self.notifications_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("schedule", self.schedule_command))
        self.application.add_handler(CommandHandler("timezone", self.timezone_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add message handler for custom input
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Set up notification scheduler
        scheduler.set_notification_callback(self.send_weather_notification)
        
        # Set up rain monitoring
        rain_monitor.set_rain_callback(self.send_rain_alert)
        
        # Set up habit tracking
        habit_tracker.set_reminder_callback(self.send_habit_reminder)
        
        # Run database migration on startup
        logger.info("Running database migration...")
        run_migration()
        
        # Set up bot menu commands
        async def post_init(app: Application) -> None:
            await self._setup_bot_menu()
        
        self.application.post_init = post_init
        
        logger.info("Teo bot is starting...")
        
        # Run the bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def _setup_bot_menu(self) -> None:
        """Set up the bot menu commands"""
        try:
            commands = [
                BotCommand("start", "🚀 Начать работу с ботом"),
                BotCommand("weather", "🌤 Текущая погода"),
                BotCommand("forecast", "📅 Прогноз погоды на 3 дня"),
                BotCommand("setcity", "🌍 Установить город по умолчанию"),
                BotCommand("notifications", "🔔 Настройки уведомлений"),
                BotCommand("schedule", "⏰ Установить время уведомлений"),
                BotCommand("timezone", "🕰 Установить часовой пояс"),
                BotCommand("settings", "⚙️ Посмотреть настройки"),
                BotCommand("help", "ℹ️ Помощь и инструкции")
            ]
            
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot menu commands have been set up")
        except Exception as e:
            logger.error(f"Failed to set up bot menu commands: {e}")


if __name__ == '__main__':
    bot = TeoBot()
    bot.run()
