"""
Single Message Bot Interface
Concept for managing bot as a single message application
"""
import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from app.database.database import DatabaseManager
from app.utils.keyboards import KeyboardBuilder
from app.utils.messages import MessageBuilder

logger = logging.getLogger(__name__)
db = DatabaseManager()


class SingleMessageBot:
    """Single message bot interface manager"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - create main message"""
        user_id = update.effective_user.id
        
        # Delete any existing messages from user
        await self._delete_user_messages(update, context)
        
        # Create main message
        message = await update.message.reply_text(
            MessageBuilder.welcome_message(update.effective_user.first_name),
            reply_markup=KeyboardBuilder.main_menu(),
            parse_mode='Markdown'
        )
        
        # Save message ID to database
        self.db.save_user_main_message(user_id, message.message_id)
        
        # Delete the /start command
        await update.message.delete()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all text messages - process and delete"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Get current state from database
        current_state = self.db.get_user_state(user_id)
        
        # Process message based on state
        if current_state == 'waiting_for_finance_sheet_url':
            await self._handle_finance_url(update, context, message_text)
        elif current_state == 'waiting_for_city':
            await self._handle_city_input(update, context, message_text)
        elif current_state == 'waiting_for_time':
            await self._handle_time_input(update, context, message_text)
        elif current_state == 'waiting_for_test_input':
            await self._handle_test_input(update, context, message_text)
        else:
            # Unknown state - show help
            await self._show_help_message(update, context)
        
        # Always delete user message
        await update.message.delete()
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries - update main message"""
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()
        
        # Get main message ID
        main_message_id = self.db.get_user_main_message_id(user_id)
        if not main_message_id:
            # Create new main message if not exists
            await self._create_main_message(update, context)
            return
        
        # Update main message based on callback
        await self._update_main_message(update, context, query.data)
    
    async def _delete_user_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Delete all messages from user in current chat"""
        try:
            # Get chat history and delete user messages
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            # Note: Telegram API doesn't allow bulk deletion of user messages
            # This is a limitation - we can only delete messages we sent
            # For full implementation, we'd need to track message IDs
            
        except TelegramError as e:
            logger.error(f"Error deleting messages: {e}")
    
    async def _create_main_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Create new main message for user"""
        user_id = update.effective_user.id
        
        # Create main message
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=MessageBuilder.welcome_message(update.effective_user.first_name),
            reply_markup=KeyboardBuilder.main_menu(),
            parse_mode='Markdown'
        )
        
        # Save to database
        self.db.save_user_main_message(user_id, message.message_id)
    
    async def _update_main_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
        """Update main message based on callback data"""
        query = update.callback_query
        user_id = query.from_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        if not main_message_id:
            return
        
        # Update message based on callback
        if callback_data == 'main_menu':
            await self._show_main_menu(update, context, main_message_id)
        elif callback_data == 'weather_menu':
            await self._show_weather_menu(update, context, main_message_id)
        elif callback_data == 'finance_menu':
            await self._show_finance_menu(update, context, main_message_id)
        elif callback_data == 'settings':
            await self._show_settings(update, context, main_message_id)
        elif callback_data == 'help':
            await self._show_help(update, context, main_message_id)
        else:
            # Handle other callbacks
            await self._handle_special_callback(update, context, callback_data, main_message_id)
    
    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
        """Show main menu"""
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=MessageBuilder.welcome_message(update.effective_user.first_name),
            reply_markup=KeyboardBuilder.main_menu(),
            parse_mode='Markdown'
        )
        
        # Clear user state
        self.db.clear_user_state(update.effective_user.id)
    
    async def _show_weather_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
        """Show weather menu"""
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text="🌤 **Погода**\n\nВыберите действие:",
            reply_markup=KeyboardBuilder.weather_menu(),
            parse_mode='Markdown'
        )
    
    async def _show_finance_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
        """Show finance menu"""
        user_id = update.effective_user.id
        finance_settings = self.db.get_finance_settings(user_id)
        
        if finance_settings:
            text = "💰 **Финансы**\n\n✅ Таблица подключена\n\nВыберите период для анализа:"
        else:
            text = "💰 **Финансы**\n\nЗдесь мы проанализируем твои расходы и доходы из Google Таблицы: динамика, категории, бюджеты, предиктивные инсайты.\n\n📋 Подключи таблицу в 2 шага: дай ссылку и выбери лист."
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=text,
            reply_markup=KeyboardBuilder.finance_connect_menu() if not finance_settings else KeyboardBuilder.finance_menu(),
            parse_mode='Markdown'
        )
    
    async def _show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
        """Show settings menu"""
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text="⚙️ **Настройки**\n\nВыберите настройку для изменения:",
            reply_markup=KeyboardBuilder.settings_menu(),
            parse_mode='Markdown'
        )
    
    async def _show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
        """Show help"""
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=MessageBuilder.help_message(),
            reply_markup=KeyboardBuilder.back_to_main(),
            parse_mode='Markdown'
        )
    
    async def _handle_finance_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
        """Handle finance sheet URL input"""
        user_id = update.effective_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        try:
            # Use the same logic as in FinanceInterface
            from app.interfaces.finance_interface import FinanceInterface
            await FinanceInterface.handle_sheet_url_input(update, context)
        except Exception as e:
            logger.error(f"Error handling finance URL: {e}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=main_message_id,
                text="❌ Произошла ошибка при обработке ссылки на таблицу.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
    
    async def _handle_city_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, city: str) -> None:
        """Handle city input"""
        user_id = update.effective_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        # Process city (implement your logic here)
        # ...
        
        # Show result
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=main_message_id,
            text=f"✅ Город изменен на **{city}**",
            reply_markup=KeyboardBuilder.settings_menu(),
            parse_mode='Markdown'
        )
        
        # Clear state
        self.db.clear_user_state(user_id)
    
    async def _handle_time_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, time_str: str) -> None:
        """Handle time input"""
        user_id = update.effective_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        # Process time (implement your logic here)
        # ...
        
        # Show result
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=main_message_id,
            text=f"✅ Время уведомлений изменено на **{time_str}**",
            reply_markup=KeyboardBuilder.settings_menu(),
            parse_mode='Markdown'
        )
        
        # Clear state
        self.db.clear_user_state(user_id)
    
    async def _show_help_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show help message for unknown input"""
        user_id = update.effective_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        if main_message_id:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=main_message_id,
                text="❓ Неизвестная команда\n\nИспользуйте кнопки для навигации.",
                reply_markup=KeyboardBuilder.back_to_main(),
                parse_mode='Markdown'
            )
        else:
            # Create new main message
            await self._create_main_message(update, context)
    
    async def _handle_special_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     callback_data: str, message_id: int) -> None:
        """Handle special callbacks (set states, etc.)"""
        user_id = update.effective_user.id
        
        if callback_data == 'finance_set_url':
            # Set state to wait for URL
            self.db.set_user_state(user_id, 'waiting_for_finance_sheet_url')
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="📝 Отправьте ссылку на вашу Google таблицу:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data='finance_menu')]
                ])
            )
        
        elif callback_data == 'change_city':
            # Set state to wait for city
            self.db.set_user_state(user_id, 'waiting_for_city')
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="🌍 Введите название города:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data='settings')]
                ])
            )
        
        elif callback_data == 'change_time':
            # Set state to wait for time
            self.db.set_user_state(user_id, 'waiting_for_time')
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="⏰ Введите время в формате ЧЧ:ММ (например, 08:00):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data='settings')]
                ])
            )
        
        # Test callbacks
        elif callback_data == 'test_weather':
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="🌤 **Тест погоды**\n\n✅ Функция работает!\n\nЭто демонстрация обновления главного сообщения.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌡️ Получить погоду", callback_data='weather_menu')],
                    [InlineKeyboardButton("🔙 Назад к тестам", callback_data='test_back')]
                ]),
                parse_mode='Markdown'
            )
        
        elif callback_data == 'test_finance':
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="💰 **Тест финансов**\n\n✅ Функция работает!\n\nЭто демонстрация обновления главного сообщения.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Показать статистику", callback_data='finance_menu')],
                    [InlineKeyboardButton("🔙 Назад к тестам", callback_data='test_back')]
                ]),
                parse_mode='Markdown'
            )
        
        elif callback_data == 'test_settings':
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="⚙️ **Тест настроек**\n\n✅ Функция работает!\n\nЭто демонстрация обновления главного сообщения.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌍 Изменить город", callback_data='change_city')],
                    [InlineKeyboardButton("🔙 Назад к тестам", callback_data='test_back')]
                ]),
                parse_mode='Markdown'
            )
        
        elif callback_data == 'test_input':
            # Set state to wait for test input
            self.db.set_user_state(user_id, 'waiting_for_test_input')
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="📝 **Тест ввода**\n\nОтправьте любое сообщение, и я его обработаю и удалю!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data='test_back')]
                ]),
                parse_mode='Markdown'
            )
        
        elif callback_data == 'test_back':
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="🧪 **Тестовый режим**\n\nЭто тестовая версия односообщенного интерфейса.\n\n"
                "Попробуйте нажать кнопки ниже:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌤 Тест погоды", callback_data='test_weather')],
                    [InlineKeyboardButton("💰 Тест финансов", callback_data='test_finance')],
                    [InlineKeyboardButton("⚙️ Тест настроек", callback_data='test_settings')],
                    [InlineKeyboardButton("📝 Тест ввода", callback_data='test_input')]
                ]),
                parse_mode='Markdown'
            )
    
    async def _handle_test_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, input_text: str) -> None:
        """Handle test input"""
        user_id = update.effective_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        # Show result
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=main_message_id,
            text=f"✅ **Тест ввода успешен!**\n\nВы отправили: **{input_text}**\n\nСообщение было обработано и автоматически удалено!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Еще раз", callback_data='test_input')],
                [InlineKeyboardButton("🔙 Назад к тестам", callback_data='test_back')]
            ]),
            parse_mode='Markdown'
        )
        
        # Clear state
        self.db.clear_user_state(user_id)
