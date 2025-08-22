#!/bin/bash

# Скрипт для запуска бота Тео
# Простой запуск: ./start_teo.sh

echo "🤖 Запускаю бота Тео..."
echo "Для остановки нажми Ctrl+C"
echo "=========================="

# Проверяем, что Python3 установлен
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Пожалуйста, установи Python3"
    exit 1
fi

# Проверяем файл .env
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Скопируй env_example в .env и заполни настройки:"
    echo "cp env_example .env"
    echo "Затем отредактируй .env с твоими токенами"
    exit 1
fi

# Запускаем бота
python3 main.py


