#!/usr/bin/env python3
"""
Simple Test Single Message Bot
Упрощенная версия тестового бота
"""

import asyncio
import sys
import os
import logging

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from src.utils.config import BOT_TOKEN
from src.database.database import DatabaseManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class SimpleTestBot:
    """Упрощенная версия тестового бота"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        
        # Создаем главное сообщение
        message = await update.message.reply_text(
            "🧪 **Тестовый бот**\n\nЭто тестовая версия односообщенного интерфейса.\n\n"
            "Попробуйте нажать кнопки ниже:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌤 Тест погоды", callback_data='test_weather')],
                [InlineKeyboardButton("💰 Тест финансов", callback_data='test_finance')],
                [InlineKeyboardButton("📝 Тест ввода", callback_data='test_input')]
            ]),
            parse_mode='Markdown'
        )
        
        # Сохраняем ID сообщения
        self.db.save_user_main_message(user_id, message.message_id)
        
        # Удаляем команду /start
        await update.message.delete()
        
        logger.info(f"Пользователь {user_id} запустил бота")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Получаем текущее состояние
        current_state = self.db.get_user_state(user_id)
        
        if current_state == 'waiting_for_test_input':
            await self.handle_test_input(update, context, message_text)
        else:
            await self.show_help(update, context)
        
        # Удаляем сообщение пользователя
        await update.message.delete()
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов"""
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()
        
        # Получаем ID главного сообщения
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        if not main_message_id:
            await self.handle_start(update, context)
            return
        
        # Обрабатываем callback
        if query.data == 'test_weather':
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=main_message_id,
                text="🌤 **Тест погоды**\n\n✅ Функция работает!\n\nЭто демонстрация обновления главного сообщения.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='back')]
                ]),
                parse_mode='Markdown'
            )
        
        elif query.data == 'test_finance':
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=main_message_id,
                text="💰 **Тест финансов**\n\n✅ Функция работает!\n\nЭто демонстрация обновления главного сообщения.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='back')]
                ]),
                parse_mode='Markdown'
            )
        
        elif query.data == 'test_input':
            # Устанавливаем состояние ожидания ввода
            self.db.set_user_state(user_id, 'waiting_for_test_input')
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=main_message_id,
                text="📝 **Тест ввода**\n\nОтправьте любое сообщение, и я его обработаю и удалю!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data='back')]
                ]),
                parse_mode='Markdown'
            )
        
        elif query.data == 'back':
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=main_message_id,
                text="🧪 **Тестовый бот**\n\nЭто тестовая версия односообщенного интерфейса.\n\n"
                "Попробуйте нажать кнопки ниже:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌤 Тест погоды", callback_data='test_weather')],
                    [InlineKeyboardButton("💰 Тест финансов", callback_data='test_finance')],
                    [InlineKeyboardButton("📝 Тест ввода", callback_data='test_input')]
                ]),
                parse_mode='Markdown'
            )
            
            # Очищаем состояние
            self.db.clear_user_state(user_id)
    
    async def handle_test_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, input_text: str):
        """Обработка тестового ввода"""
        user_id = update.effective_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        # Показываем результат
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=main_message_id,
            text=f"✅ **Тест ввода успешен!**\n\nВы отправили: **{input_text}**\n\nСообщение было обработано и автоматически удалено!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Еще раз", callback_data='test_input')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back')]
            ]),
            parse_mode='Markdown'
        )
        
        # Очищаем состояние
        self.db.clear_user_state(user_id)
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать справку"""
        user_id = update.effective_user.id
        main_message_id = self.db.get_user_main_message_id(user_id)
        
        if main_message_id:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=main_message_id,
                text="❓ Неизвестная команда\n\nИспользуйте кнопки для навигации.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='back')]
                ]),
                parse_mode='Markdown'
            )
        else:
            await self.handle_start(update, context)


async def main():
    """Главная функция"""
    print("🧪 Запуск упрощенного тестового бота...")
    print("📱 Используйте команду /start в боте для тестирования")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    # Создаем бота
    bot = SimpleTestBot()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot.handle_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    print("✅ Бот запущен! Отправьте /start в Telegram")
    
    # Запускаем бота
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())


