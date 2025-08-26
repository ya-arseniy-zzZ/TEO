#!/bin/bash

# Скрипт для проверки статуса Teo Bot на сервере Timeweb
# Использование: ./check-timeweb.sh

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

log "🔍 Проверяю статус Teo Bot на сервере Timeweb: $SERVER_IP"

# Проверяем SSH подключение
log "Проверяем подключение к серверу..."
if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@$SERVER_IP 'echo "SSH подключение работает"' 2>/dev/null; then
    error "❌ Не удается подключиться к серверу $SERVER_IP"
    exit 1
fi

log "✅ Подключение к серверу установлено"

# Подключаемся к серверу и проверяем статус
ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'EOF'
    echo "=== СТАТУС TEO BOT ==="
    
    # Проверяем статус systemd сервиса
    echo "📊 Статус systemd сервиса:"
    if systemctl is-active teo-bot.service &> /dev/null; then
        echo "🟢 Сервис ЗАПУЩЕН"
        echo "📋 Детали сервиса:"
        systemctl status teo-bot.service --no-pager -l
    else
        echo "🔴 Сервис ОСТАНОВЛЕН"
    fi
    
    # Проверяем процессы Python
    echo -e "\n📊 Процессы Python:"
    if pgrep -f "python.*main.py" > /dev/null; then
        echo "🟢 Найдены процессы Python:"
        ps aux | grep "python.*main.py" | grep -v grep
    else
        echo "🔴 Процессы Python не найдены"
    fi
    
    # Проверяем Docker контейнеры
    echo -e "\n📊 Docker контейнеры:"
    if command -v docker-compose &> /dev/null; then
        cd /root/teo-bot
        if [ -f "docker-compose.yml" ]; then
            echo "📋 Статус Docker контейнеров:"
            docker-compose ps
        else
            echo "📋 Docker-compose.yml не найден"
        fi
    else
        echo "📋 Docker-compose не установлен"
    fi
    
    # Проверяем использование ресурсов
    echo -e "\n📊 Использование ресурсов:"
    echo "CPU и память:"
    top -bn1 | head -5
    
    echo -e "\n📊 Использование диска:"
    df -h / | tail -1
    
    # Проверяем логи сервиса
    echo -e "\n📊 Последние логи сервиса (если есть):"
    if systemctl is-active teo-bot.service &> /dev/null; then
        journalctl -u teo-bot.service --no-pager -n 5
    else
        echo "Сервис остановлен, логи недоступны"
    fi
    
    echo -e "\n=== ПРОВЕРКА ЗАВЕРШЕНА ==="
EOF

if [ $? -eq 0 ]; then
    log "✅ Проверка статуса завершена"
else
    error "❌ Ошибка при проверке статуса"
    exit 1
fi
