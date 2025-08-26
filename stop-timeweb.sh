#!/bin/bash

# Скрипт для остановки Teo Bot на сервере Timeweb
# Использование: ./stop-timeweb.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

SERVER_IP="62.113.36.171"

log "🛑 Останавливаю Teo Bot на сервере Timeweb: $SERVER_IP"

# Проверяем SSH подключение
log "Проверяем подключение к серверу..."
if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@$SERVER_IP 'echo "SSH подключение работает"' 2>/dev/null; then
    error "❌ Не удается подключиться к серверу $SERVER_IP"
    error "Проверьте:"
    error "1. Доступность сервера"
    error "2. SSH ключи"
    error "3. IP адрес сервера"
    exit 1
fi

log "✅ Подключение к серверу установлено"

# Подключаемся к серверу и останавливаем бота
ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'EOF'
    echo "=== ОСТАНОВКА TEO BOT ==="
    
    # Проверяем статус сервиса перед остановкой
    echo "📊 Статус сервиса перед остановкой:"
    if systemctl is-active teo-bot.service &> /dev/null; then
        echo "✅ Сервис запущен"
    else
        echo "❌ Сервис не запущен"
        exit 0
    fi
    
    # Останавливаем systemd сервис
    echo -e "\n🛑 Останавливаю systemd сервис..."
    systemctl stop teo-bot.service
    
    # Проверяем, что сервис остановлен
    echo -e "\n📊 Проверяю статус после остановки:"
    if systemctl is-active teo-bot.service &> /dev/null; then
        echo "❌ Сервис все еще запущен"
        exit 1
    else
        echo "✅ Сервис успешно остановлен"
    fi
    
    # Проверяем, что нет процессов Python с ботом
    echo -e "\n📊 Проверяю процессы Python:"
    if pgrep -f "python.*main.py" > /dev/null; then
        echo "⚠️  Найдены процессы Python, завершаю их..."
        pkill -f "python.*main.py" || true
        sleep 2
    else
        echo "✅ Процессы Python не найдены"
    fi
    
    # Проверяем Docker контейнеры (если используются)
    echo -e "\n📊 Проверяю Docker контейнеры:"
    if command -v docker-compose &> /dev/null; then
        cd /root/teo-bot
        if [ -f "docker-compose.yml" ]; then
            echo "📋 Останавливаю Docker контейнеры..."
            docker-compose down || true
        fi
    fi
    
    # Проверяем использование ресурсов
    echo -e "\n📊 Использование ресурсов после остановки:"
    echo "CPU и память:"
    top -bn1 | head -5
    
    echo -e "\n=== БОТ УСПЕШНО ОСТАНОВЛЕН ==="
EOF

if [ $? -eq 0 ]; then
    log "✅ Teo Bot успешно остановлен на сервере Timeweb"
    log "💡 Для запуска бота используйте: ./start-timeweb.sh"
    log "💡 Для проверки статуса используйте: ./check-timeweb.sh"
else
    error "❌ Ошибка при остановке бота"
    exit 1
fi
