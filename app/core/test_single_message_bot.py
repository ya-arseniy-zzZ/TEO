"""
Test Single Message Bot
Тестовая версия бота с односообщенным интерфейсом
"""
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

from app.core.single_message_bot import SingleMessageBot
from app.utils.config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TestSingleMessageBot:
    """Тестовая версия бота с односообщенным интерфейсом"""
    
    def __init__(self):
        self.single_message_bot = SingleMessageBot()
        self.application = None
    
    async def start(self):
        """Запустить тестового бота"""
        # Создаем приложение
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.single_message_bot.handle_start))
        self.application.add_handler(CommandHandler("test", self.handle_test_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.single_message_bot.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.single_message_bot.handle_callback))
        
        # Добавляем обработчик ошибок
        self.application.add_error_handler(self.error_handler)
        
        logger.info("Тестовый бот запущен!")
        logger.info("Используйте /test для тестирования функций")
        
        # Запускаем бота
        await self.application.run_polling()
    
    async def handle_test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test для тестирования"""
        user_id = update.effective_user.id
        
        # Создаем тестовое главное сообщение
        message = await update.message.reply_text(
            "🧪 **Тестовый режим**\n\nЭто тестовая версия односообщенного интерфейса.\n\n"
            "Попробуйте нажать кнопки ниже:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌤 Тест погоды", callback_data='test_weather')],
                [InlineKeyboardButton("💰 Тест финансов", callback_data='test_finance')],
                [InlineKeyboardButton("⚙️ Тест настроек", callback_data='test_settings')],
                [InlineKeyboardButton("📝 Тест ввода", callback_data='test_input')]
            ]),
            parse_mode='Markdown'
        )
        
        # Сохраняем ID сообщения
        self.single_message_bot.db.save_user_main_message(user_id, message.message_id)
        
        # Удаляем команду /test
        await update.message.delete()
        
        logger.info(f"Пользователь {user_id} запустил тестовый режим")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка в боте: {context.error}")
        
        if update and update.effective_user:
            user_id = update.effective_user.id
            main_message_id = self.single_message_bot.db.get_user_main_message_id(user_id)
            
            if main_message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=main_message_id,
                        text="❌ **Произошла ошибка**\n\nПопробуйте еще раз или используйте /test для перезапуска.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Перезапустить", callback_data='main_menu')]
                        ]),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Не удалось обновить сообщение об ошибке: {e}")


async def main():
    """Главная функция"""
    bot = TestSingleMessageBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
