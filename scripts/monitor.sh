#!/bin/bash

# Скрипт для мониторинга Teo Bot на сервере
# Использование: ./monitor.sh [instance-name]

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

# Получаем имя инстанса из аргумента или используем по умолчанию
INSTANCE_NAME=${1:-"teo-bot-instance"}

log "Проверяем состояние Teo Bot на инстансе: $INSTANCE_NAME"

# Проверяем существование инстанса
if ! yc compute instance get $INSTANCE_NAME &> /dev/null; then
    error "Инстанс $INSTANCE_NAME не найден!"
    exit 1
fi

# Получаем внешний IP адрес инстанса
INSTANCE_IP=$(yc compute instance get $INSTANCE_NAME --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')

info "IP адрес инстанса: $INSTANCE_IP"

# Проверяем статус инстанса
INSTANCE_STATUS=$(yc compute instance get $INSTANCE_NAME --format=json | jq -r '.status')
if [ "$INSTANCE_STATUS" = "RUNNING" ]; then
    log "✅ Инстанс запущен"
else
    error "❌ Инстанс не запущен (статус: $INSTANCE_STATUS)"
    exit 1
fi

# Подключаемся к серверу и проверяем состояние
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    echo "=== ПРОВЕРКА СИСТЕМЫ ==="
    
    # Проверяем использование диска
    echo "📊 Использование диска:"
    df -h / | tail -1
    
    # Проверяем использование памяти
    echo -e "\n📊 Использование памяти:"
    free -h
    
    # Проверяем загрузку CPU
    echo -e "\n📊 Загрузка CPU:"
    uptime
    
    echo -e "\n=== ПРОВЕРКА DOCKER ==="
    
    # Проверяем статус Docker
    if systemctl is-active --quiet docker; then
        echo "✅ Docker запущен"
    else
        echo "❌ Docker не запущен"
        exit 1
    fi
    
    # Проверяем контейнеры
    echo -e "\n📊 Статус контейнеров:"
    cd /home/ubuntu/teo-bot
    docker-compose ps
    
    echo -e "\n=== ПРОВЕРКА СЕРВИСА ==="
    
    # Проверяем systemd сервис
    echo "📊 Статус systemd сервиса:"
    sudo systemctl is-active teo-bot.service
    
    echo -e "\n📊 Последние логи сервиса:"
    sudo journalctl -u teo-bot.service --no-pager -n 10
    
    echo -e "\n=== ПРОВЕРКА ПРИЛОЖЕНИЯ ==="
    
    # Проверяем логи приложения
    echo "📊 Последние логи приложения:"
    docker-compose logs --tail=10
    
    # Проверяем переменные окружения
    echo -e "\n📊 Проверка переменных окружения:"
    docker-compose exec -T teo-bot env | grep -E "(TELEGRAM_BOT_TOKEN|WEATHER_API_KEY|DEFAULT_CITY|TIMEZONE)" || echo "Переменные окружения не найдены"
    
    # Проверяем файлы данных
    echo -e "\n📊 Проверка файлов данных:"
    if [ -f teo_bot.db ]; then
        echo "✅ База данных найдена ($(ls -lh teo_bot.db | awk '{print $5}'))"
    else
        echo "❌ База данных не найдена"
    fi
    
    if [ -f user_habits.json ]; then
        echo "✅ Файл привычек найден ($(ls -lh user_habits.json | awk '{print $5}'))"
    else
        echo "❌ Файл привычек не найден"
    fi
    
    # Проверяем резервные копии
    echo -e "\n📊 Резервные копии:"
    if [ -d backups ]; then
        echo "✅ Папка бэкапов найдена"
        ls -la backups/ | tail -5
    else
        echo "❌ Папка бэкапов не найдена"
    fi
    
    echo -e "\n=== ПРОВЕРКА СЕТИ ==="
    
    # Проверяем подключение к интернету
    if ping -c 1 8.8.8.8 &> /dev/null; then
        echo "✅ Интернет доступен"
    else
        echo "❌ Проблемы с интернетом"
    fi
    
    # Проверяем подключение к Telegram API
    if curl -s https://api.telegram.org &> /dev/null; then
        echo "✅ Telegram API доступен"
    else
        echo "❌ Проблемы с Telegram API"
    fi
    
    echo -e "\n=== РЕКОМЕНДАЦИИ ==="
    
    # Проверяем свободное место
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 80 ]; then
        echo "⚠️  Мало места на диске ($DISK_USAGE%)"
    else
        echo "✅ Места на диске достаточно ($DISK_USAGE%)"
    fi
    
    # Проверяем время работы системы
    UPTIME_DAYS=$(uptime | awk '{print $3}' | sed 's/,//')
    echo "📅 Система работает: $UPTIME_DAYS"
    
    # Проверяем последние обновления
    LAST_UPDATE=$(stat -c %Y /var/cache/apt/ 2>/dev/null || echo 0)
    CURRENT_TIME=$(date +%s)
    DAYS_SINCE_UPDATE=$(( (CURRENT_TIME - LAST_UPDATE) / 86400 ))
    
    if [ "$DAYS_SINCE_UPDATE" -gt 7 ]; then
        echo "⚠️  Система не обновлялась $DAYS_SINCE_UPDATE дней"
    else
        echo "✅ Система обновлена недавно"
    fi
EOF

log "Мониторинг завершен!"
