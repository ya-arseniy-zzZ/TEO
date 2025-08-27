"""
Helper functions for Anchor-UX system
Provides utility functions for common Anchor-UX operations
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from .anchor_ux import (
    anchor_ux_manager, AnchorKeyboardBuilder, AnchorMessageBuilder,
    ScreenState, InputType, AwaitingInput
)

logger = logging.getLogger(__name__)


async def edit_anchor_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             text: str, keyboard: Optional[List[List[Dict[str, str]]]] = None,
                             parse_mode: str = 'Markdown') -> bool:
    """
    Edit anchor message safely with error handling
    
    Returns:
        bool: True if successful, False if anchor message was lost
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    anchor_message_id = anchor_ux_manager.get_anchor_message_id(user_id, chat_id)
    
    if not anchor_message_id:
        logger.warning(f"No anchor message found for user {user_id}")
        return False
    
    try:
        # Convert keyboard dict to InlineKeyboardMarkup
        reply_markup = None
        if keyboard:
            # Convert dict format to InlineKeyboardButton objects
            inline_keyboard = []
            for row in keyboard:
                button_row = []
                for button in row:
                    button_row.append(InlineKeyboardButton(
                        text=button["text"],
                        callback_data=button["callback_data"]
                    ))
                inline_keyboard.append(button_row)
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
        
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=anchor_message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
        
    except BadRequest as e:
        if "Message is not modified" in str(e):
            # Message content is the same, this is fine
            logger.debug(f"Message not modified for user {user_id}: {e}")
            return True
        elif "Message to edit not found" in str(e):
            # Anchor message was deleted, need to create new one
            logger.warning(f"Anchor message not found for user {user_id}, will create new one")
            return False
        else:
            logger.error(f"Error editing anchor message for user {user_id}: {e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error editing anchor message for user {user_id}: {e}")
        return False


async def create_new_anchor_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   text: str, keyboard: Optional[List[List[Dict[str, str]]]] = None,
                                   parse_mode: str = 'Markdown') -> bool:
    """
    Create new anchor message and save its ID
    
    Returns:
        bool: True if successful, False otherwise
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        # Convert keyboard dict to InlineKeyboardMarkup
        reply_markup = None
        if keyboard:
            inline_keyboard = []
            for row in keyboard:
                button_row = []
                for button in row:
                    button_row.append(InlineKeyboardButton(
                        text=button["text"],
                        callback_data=button["callback_data"]
                    ))
                inline_keyboard.append(button_row)
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
        
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        
        # Save new anchor message ID
        anchor_ux_manager.set_anchor_message(user_id, chat_id, message.message_id)
        
        # Add notification about screen refresh
        await context.bot.send_message(
            chat_id=chat_id,
            text="🔄 Обновил экран, продолжаем.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Скрыть", callback_data="hide_notification")
            ]])
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating new anchor message for user {user_id}: {e}")
        return False


async def show_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     screen: ScreenState) -> bool:
    """
    Show screen by editing anchor message
    
    Returns:
        bool: True if successful, False if anchor message was lost
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Build message text
    awaiting_input = anchor_ux_manager.get_awaiting_input(user_id, chat_id)
    text = AnchorMessageBuilder.build_screen_message(
        title=screen.title,
        content=screen.content,
        status=screen.status,
        awaiting_input=awaiting_input
    )
    
    # Try to edit existing anchor message
    success = await edit_anchor_message(update, context, text, screen.keyboard)
    
    if not success:
        # Anchor message was lost, create new one
        success = await create_new_anchor_message(update, context, text, screen.keyboard)
    
    if success:
        # Update current screen in session
        anchor_ux_manager.set_current_screen(user_id, chat_id, screen)
    
    return success


async def handle_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   action: str) -> bool:
    """
    Handle navigation callbacks (back, main menu)
    
    Returns:
        bool: True if handled, False otherwise
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if action == "nav_back":
        # Go back to previous screen
        previous_screen = anchor_ux_manager.go_back(user_id, chat_id)
        if previous_screen:
            await show_screen(update, context, previous_screen)
            return True
        else:
            # No previous screen, go to main menu
            await show_main_menu(update, context)
            return True
    
    elif action == "nav_main":
        # Go to main menu
        await show_main_menu(update, context)
        return True
    
    elif action == "hide_notification":
        # Hide notification message
        try:
            await update.callback_query.message.delete()
        except Exception as e:
            logger.error(f"Error hiding notification: {e}")
        return True
    
    return False


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Show main menu screen
    
    Returns:
        bool: True if successful, False otherwise
    """
    from .messages import MessageBuilder
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Clear any awaiting input
    anchor_ux_manager.clear_awaiting_input(user_id, chat_id)
    
    # Create main menu screen
    screen = ScreenState(
        screen_id="main_menu",
        params={},
        title="🏠 Главное меню",
        content=MessageBuilder.welcome_message(update.effective_user.first_name),
        status="",
        keyboard=[
            [{"text": "🌤 Погода", "callback_data": "weather_menu"}],
            [{"text": "📰 Новости", "callback_data": "news_menu"}],
            [{"text": "🎯 Привычки", "callback_data": "habits_menu"}],
            [{"text": "💰 Финансы", "callback_data": "finance_menu"}],
            [{"text": "⚙️ Настройки", "callback_data": "settings"}],
            [{"text": "❓ Помощь", "callback_data": "help"}]
        ],
        created_at=datetime.now()
    )
    
    return await show_screen(update, context, screen)


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle text input when awaiting input
    
    Returns:
        bool: True if input was handled, False otherwise
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    # Check if user is awaiting input
    awaiting_input = anchor_ux_manager.get_awaiting_input(user_id, chat_id)
    if not awaiting_input:
        return False
    
    # Check if input has expired
    if awaiting_input.is_expired():
        anchor_ux_manager.clear_awaiting_input(user_id, chat_id)
        
        # Show expired message
        screen = ScreenState(
            screen_id="input_expired",
            params={},
            title="⏰ Время истекло",
            content="Ввод отменён из-за бездействия.",
            status="",
            keyboard=[[{"text": "🔄 Повторить ввод", "callback_data": "retry_input"}]],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
        return True
    
    # Validate input
    is_valid, error_message = anchor_ux_manager.validate_input(awaiting_input.type, text)
    
    if not is_valid:
        # Show error and keep awaiting input
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ {error_message}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Скрыть", callback_data="hide_notification")
            ]])
        )
        return True
    
    # Input is valid, clear awaiting input
    anchor_ux_manager.clear_awaiting_input(user_id, chat_id)
    
    # Try to delete user message (if possible)
    try:
        await update.message.delete()
    except Exception as e:
        logger.debug(f"Could not delete user message: {e}")
        # Send ephemeral message about data being processed
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Данные получены и обработаны.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Скрыть", callback_data="hide_notification")
            ]])
        )
    
    # Process the input based on context
    await process_validated_input(update, context, text, awaiting_input)
    
    return True


async def process_validated_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 text: str, awaiting_input: AwaitingInput):
    """
    Process validated input based on context
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Get context from awaiting input
    input_context = awaiting_input.context or {}
    input_type = awaiting_input.type
    
    # Process based on input type and context
    if input_type == InputType.URL and "finance_sheet" in input_context:
        # Handle Google Sheets URL for finance
        await handle_finance_sheet_url(update, context, text)
    
    elif input_type == InputType.TEXT and "habit_name" in input_context:
        # Handle habit name input
        await handle_habit_name_input(update, context, text)
    
    elif input_type == InputType.TEXT and "habit_description" in input_context:
        # Handle habit description input
        await handle_habit_description_input(update, context, text)
    
    elif input_type == InputType.TIME and "notification_time" in input_context:
        # Handle notification time input
        await handle_notification_time_input(update, context, text)
    
    elif input_type == InputType.TEXT and "city_name" in input_context:
        # Handle city name input
        await handle_city_input(update, context, text)
    
    else:
        # Generic text input handling
        await handle_generic_text_input(update, context, text, input_context)


async def handle_finance_sheet_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Handle Google Sheets URL input for finance"""
    from src.interfaces.finance_interface import FinanceInterface
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        # Process the URL through finance interface
        await FinanceInterface.handle_sheet_url_input(update, context, url)
        
        # Show success message
        screen = ScreenState(
            screen_id="finance_sheet_connected",
            params={"url": url},
            title="✅ Таблица подключена",
            content="Google Таблица успешно подключена! Теперь можно анализировать финансы.",
            status="",
            keyboard=[
                [{"text": "📊 Запустить анализ", "callback_data": "finance_analyze"}],
                [{"text": "⚙️ Настройки", "callback_data": "finance_settings"}],
                [{"text": "🔙 Назад", "callback_data": "finance_menu"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)
        
    except Exception as e:
        logger.error(f"Error handling finance sheet URL: {e}")
        
        # Show error screen
        screen = ScreenState(
            screen_id="finance_error",
            params={},
            title="❌ Ошибка подключения",
            content=f"Не удалось подключить таблицу: {str(e)}",
            status="",
            keyboard=[
                [{"text": "🔄 Попробовать снова", "callback_data": "finance_connect"}],
                [{"text": "🔙 Назад", "callback_data": "finance_menu"}]
            ],
            created_at=datetime.now()
        )
        
        await show_screen(update, context, screen)


async def handle_habit_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str):
    """Handle habit name input"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Store habit name in context
    context.user_data['habit_name'] = name
    
    # Set awaiting input for description
    anchor_ux_manager.set_awaiting_input(
        user_id, chat_id,
        InputType.TEXT,
        "описание привычки",
        context={"habit_description": True}
    )
    
    # Show description input screen
    screen = ScreenState(
        screen_id="habit_description_input",
        params={"name": name},
        title="📝 Описание привычки",
        content=f"Название: **{name}**\n\nТеперь добавьте описание привычки (необязательно):",
        status="",
        keyboard=[
            [{"text": "⏭ Пропустить", "callback_data": "habit_skip_description"}],
            [{"text": "🔙 Назад", "callback_data": "habit_create"}]
        ],
        created_at=datetime.now()
    )
    
    await show_screen(update, context, screen)


async def handle_habit_description_input(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str):
    """Handle habit description input"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Store habit description in context
    context.user_data['habit_description'] = description
    
    # Create the habit
    from src.services.habit_tracker import habit_tracker
    
    habit_name = context.user_data.get('habit_name', 'Новая привычка')
    habit_id = habit_tracker.create_habit(
        user_id=user_id,
        name=habit_name,
        description=description
    )
    
    # Show success screen
    screen = ScreenState(
        screen_id="habit_created",
        params={"habit_id": habit_id},
        title="✅ Привычка создана",
        content=f"Привычка **{habit_name}** успешно создана!",
        status="",
        keyboard=[
            [{"text": "📋 Мои привычки", "callback_data": "view_habits"}],
            [{"text": "➕ Создать ещё", "callback_data": "create_habit"}],
            [{"text": "🔙 Назад", "callback_data": "habits_menu"}]
        ],
        created_at=datetime.now()
    )
    
    await show_screen(update, context, screen)


async def handle_notification_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE, time_str: str):
    """Handle notification time input"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Update notification time in database
    from src.database.database import db
    db.update_notification_time(user_id, time_str)
    
    # Show success screen
    screen = ScreenState(
        screen_id="notification_time_updated",
        params={"time": time_str},
        title="✅ Время обновлено",
        content=f"Время уведомлений установлено на **{time_str}**",
        status="",
        keyboard=[
            [{"text": "⚙️ Настройки", "callback_data": "settings"}],
            [{"text": "🔙 Назад", "callback_data": "notifications_menu"}]
        ],
        created_at=datetime.now()
    )
    
    await show_screen(update, context, screen)


async def handle_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE, city: str):
    """Handle city name input"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Update city in database
    from src.database.database import db
    db.update_user_city(user_id, city)
    
    # Show success screen
    screen = ScreenState(
        screen_id="city_updated",
        params={"city": city},
        title="✅ Город обновлён",
        content=f"Город установлен: **{city}**",
        status="",
        keyboard=[
            [{"text": "🌤 Погода", "callback_data": "current_weather"}],
            [{"text": "⚙️ Настройки", "callback_data": "settings"}],
            [{"text": "🔙 Назад", "callback_data": "weather_menu"}]
        ],
        created_at=datetime.now()
    )
    
    await show_screen(update, context, screen)


async def handle_generic_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   text: str, input_context: Dict[str, Any]):
    """Handle generic text input"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Show generic success message
    screen = ScreenState(
        screen_id="input_processed",
        params={"text": text},
        title="✅ Данные получены",
        content=f"Получено: **{text}**",
        status="",
        keyboard=[
            [{"text": "🔙 Назад", "callback_data": "nav_back"}],
            [{"text": "🏠 Главное меню", "callback_data": "nav_main"}]
        ],
        created_at=datetime.now()
    )
    
    await show_screen(update, context, screen)


async def answer_callback_query_safely(update: Update, text: str = "", show_alert: bool = False):
    """Safely answer callback query with error handling"""
    try:
        await update.callback_query.answer(text=text, show_alert=show_alert)
    except Exception as e:
        logger.error(f"Error answering callback query: {e}")


async def show_loading_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             message: str = "Обрабатываю...") -> bool:
    """Show loading screen while processing"""
    screen = ScreenState(
        screen_id="loading",
        params={},
        title="⏳ Обработка",
        content=message,
        status="",
        keyboard=[],
        created_at=datetime.now()
    )
    
    return await show_screen(update, context, screen)
