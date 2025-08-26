#!/usr/bin/env python3
"""
Test Single Message Bot Runner
Запуск тестовой версии бота с односообщенным интерфейсом
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.test_single_message_bot import TestSingleMessageBot


async def main():
    """Главная функция"""
    print("🧪 Запуск тестового бота с односообщенным интерфейсом...")
    print("📱 Используйте команду /test в боте для тестирования")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    try:
        bot = TestSingleMessageBot()
        await bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())



