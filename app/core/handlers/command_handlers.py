"""
Command handlers for Teo bot
Extracted from main bot file to improve modularity
"""
import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.utils.keyboards import KeyboardBuilder
from app.utils.messages import MessageBuilder
from app.utils.error_handler import ErrorHandler
from app.utils.constants import EMOJIS, DEFAULT_CITY
from app.services.weather_service import WeatherService
from app.database.database import DatabaseManager

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Handlers for bot commands"""
    
    def __init__(self, weather_service: WeatherService, db: DatabaseManager):
        self.weather_service = weather_service
        self.db = db
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            user_name = update.effective_user.first_name
            
            # Initialize user in database
            self.db.create_or_update_user(
                user_id=user_id,
                username=update.effective_user.username,
                first_name=user_name
            )
            
            welcome_message = MessageBuilder.welcome_message(user_name)
            keyboard = KeyboardBuilder.back_to_main()
            
            try:
                # Use custom bot avatar image for start command
                with open('assets/bot_avatar_for_start.jpeg', 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=welcome_message,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
            except FileNotFoundError:
                # Fallback to text message if image file not found
                logger.warning("Start avatar image not found, using text message")
                await update.message.reply_text(
                    welcome_message, 
                    reply_markup=keyboard, 
                    parse_mode='Markdown'
                )
            except Exception as e:
                # Fallback to text message if error
                logger.error(f"Error displaying start avatar: {e}")
                await update.message.reply_text(
                    welcome_message, 
                    reply_markup=keyboard, 
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await ErrorHandler.handle_error(update, context, e, "start_command")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        try:
            help_message = MessageBuilder.help_message()
            keyboard = KeyboardBuilder.back_to_main()
            
            await update.message.reply_text(
                help_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            await ErrorHandler.handle_error(update, context, e, "help_command")
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /weather command"""
        try:
            user_id = update.effective_user.id
            
            # Get city from command args or user settings
            if context.args:
                city = ' '.join(context.args)
            else:
                weather_settings = self.db.get_weather_settings(user_id)
                city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            
            # Send typing indicator
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action='typing'
            )
            
            # Fetch weather data
            weather_data = self.weather_service.get_current_weather(city)
            message = self.weather_service.format_weather_message(weather_data)
            
            # Add navigation buttons
            keyboard = KeyboardBuilder.weather_actions()
            
            await update.message.reply_text(
                message, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
        except Exception as e:
            await ErrorHandler.handle_error(update, context, e, "weather_command")
    
    async def forecast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /forecast command"""
        try:
            user_id = update.effective_user.id
            
            # Get city from command args or user settings
            if context.args:
                city = ' '.join(context.args)
            else:
                weather_settings = self.db.get_weather_settings(user_id)
                city = weather_settings.get('city', DEFAULT_CITY) if weather_settings else DEFAULT_CITY
            
            # Send typing indicator
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action='typing'
            )
            
            # Fetch forecast data
            forecast_data = self.weather_service.get_weather_forecast(city)
            message = self.weather_service.format_forecast_message(forecast_data)
            
            # Add navigation buttons
            keyboard = KeyboardBuilder.forecast_actions()
            
            await update.message.reply_text(
                message, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
        except Exception as e:
            await ErrorHandler.handle_error(update, context, e, "forecast_command")
    
    async def setcity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /setcity command"""
        try:
            user_id = update.effective_user.id
            
            if not context.args:
                await update.message.reply_text(
                    "Пожалуйста, укажи город. Пример: `/setcity Москва`", 
                    parse_mode='Markdown'
                )
                return
            
            city = ' '.join(context.args)
            
            # Test if the city is valid by fetching weather
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action='typing'
            )
            weather_data = self.weather_service.get_current_weather(city)
            
            if weather_data:
                # Update city in database
                self.db.update_weather_settings(user_id, city=weather_data['city'])
                
                message = (
                    f"{EMOJIS['success']} Твой город по умолчанию установлен: "
                    f"**{weather_data['city']}, {weather_data['country']}**"
                )
                
                # Add navigation buttons
                keyboard = [
                    [KeyboardBuilder.weather_actions().inline_keyboard[0][0]],  # Refresh button
                    [KeyboardBuilder.weather_actions().inline_keyboard[2][0]],  # Weather menu
                    [KeyboardBuilder.weather_actions().inline_keyboard[2][1]]   # Main menu
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message, 
                    reply_markup=reply_markup, 
                    parse_mode='Markdown'
                )
            else:
                message = f"{EMOJIS['error']} Не удалось найти город '{city}'. Проверь правописание и попробуй ещё раз."
                
                keyboard = [
                    [InlineKeyboardButton("🔙 К выбору городов", callback_data='city_page_0')],
                    [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message, 
                    reply_markup=reply_markup, 
                    parse_mode='Markdown'
                )
        except Exception as e:
            await ErrorHandler.handle_error(update, context, e, "setcity_command")
    
    async def notifications_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /notifications command"""
        try:
            user_id = update.effective_user.id
            
            # Get user settings
            weather_settings = self.db.get_weather_settings(user_id)
            
            if weather_settings:
                notifications_enabled = weather_settings.get('daily_notifications_enabled', False)
                notification_time = weather_settings.get('notification_time', '08:00')
                rain_alerts_enabled = weather_settings.get('rain_alerts_enabled', True)
                
                status_emoji = EMOJIS['success'] if notifications_enabled else EMOJIS['error']
                rain_emoji = EMOJIS['success'] if rain_alerts_enabled else EMOJIS['error']
                
                message = (
                    f"🔔 **Настройки уведомлений**\n\n"
                    f"Ежедневные уведомления: {status_emoji} "
                    f"{'Включены' if notifications_enabled else 'Отключены'}\n"
                    f"Время: {notification_time}\n\n"
                    f"Уведомления о дожде: {rain_emoji} "
                    f"{'Включены' if rain_alerts_enabled else 'Отключены'}\n\n"
                    f"Используй кнопки ниже для настройки:"
                )
            else:
                message = (
                    "🔔 **Настройки уведомлений**\n\n"
                    "Уведомления не настроены.\n"
                    "Используй кнопки ниже для настройки:"
                )
            
            keyboard = KeyboardBuilder.notifications_menu()
            
            await update.message.reply_text(
                message, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
        except Exception as e:
            await ErrorHandler.handle_error(update, context, e, "notifications_command")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command"""
        try:
            user_id = update.effective_user.id
            
            # Get user settings
            weather_settings = self.db.get_weather_settings(user_id)
            
            if weather_settings:
                city = weather_settings.get('city', DEFAULT_CITY)
                timezone = weather_settings.get('timezone', 'UTC')
                notification_time = weather_settings.get('notification_time', '08:00')
                notifications_enabled = weather_settings.get('daily_notifications_enabled', False)
                rain_alerts_enabled = weather_settings.get('rain_alerts_enabled', True)
                
                status_emoji = EMOJIS['success'] if notifications_enabled else EMOJIS['error']
                rain_emoji = EMOJIS['success'] if rain_alerts_enabled else EMOJIS['error']
                
                message = (
                    f"⚙️ **Настройки**\n\n"
                    f"🌍 Город: {city}\n"
                    f"🌐 Часовой пояс: {timezone}\n"
                    f"⏰ Время уведомлений: {notification_time}\n"
                    f"🔔 Ежедневные уведомления: {status_emoji} "
                    f"{'Включены' if notifications_enabled else 'Отключены'}\n"
                    f"🌧 Уведомления о дожде: {rain_emoji} "
                    f"{'Включены' if rain_alerts_enabled else 'Отключены'}\n\n"
                    f"Используй кнопки ниже для изменения настроек:"
                )
            else:
                message = (
                    "⚙️ **Настройки**\n\n"
                    "Настройки не найдены.\n"
                    "Используй кнопки ниже для настройки:"
                )
            
            keyboard = KeyboardBuilder.settings_menu()
            
            await update.message.reply_text(
                message, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
        except Exception as e:
            await ErrorHandler.handle_error(update, context, e, "settings_command")
