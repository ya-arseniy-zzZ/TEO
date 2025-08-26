#!/bin/bash

# Скрипт для остановки бота Тео на сервере
# Использование: ./stop_teo.sh [instance-name]

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

log "Останавливаю Teo Bot на инстансе: $INSTANCE_NAME"

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
if [ "$INSTANCE_STATUS" != "RUNNING" ]; then
    error "❌ Инстанс не запущен (статус: $INSTANCE_STATUS)"
    exit 1
fi

log "✅ Инстанс запущен, подключаюсь для остановки бота..."

# Подключаемся к серверу и останавливаем бота
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    echo "=== ОСТАНОВКА TEO BOT ==="
    
    # Проверяем статус сервиса перед остановкой
    echo "📊 Статус сервиса перед остановкой:"
    sudo systemctl is-active teo-bot.service
    
    # Останавливаем systemd сервис
    echo -e "\n🛑 Останавливаю systemd сервис..."
    sudo systemctl stop teo-bot.service
    
    # Проверяем, что сервис остановлен
    echo -e "\n📊 Проверяю статус после остановки:"
    if sudo systemctl is-active teo-bot.service &> /dev/null; then
        echo "❌ Сервис все еще запущен"
        exit 1
    else
        echo "✅ Сервис успешно остановлен"
    fi
    
    # Проверяем, что нет процессов Python с ботом
    echo -e "\n📊 Проверяю процессы Python:"
    if pgrep -f "python.*main.py" > /dev/null; then
        echo "⚠️  Найдены процессы Python, завершаю их..."
        sudo pkill -f "python.*main.py" || true
        sleep 2
    else
        echo "✅ Процессы Python не найдены"
    fi
    
    # Проверяем Docker контейнеры (если используются)
    echo -e "\n📊 Проверяю Docker контейнеры:"
    if command -v docker-compose &> /dev/null; then
        cd /home/ubuntu/teo-bot
        if [ -f "docker-compose.yml" ]; then
            echo "📋 Останавливаю Docker контейнеры..."
            docker-compose down || true
        fi
    fi
    
    echo -e "\n=== БОТ УСПЕШНО ОСТАНОВЛЕН ==="
EOF

if [ $? -eq 0 ]; then
    log "✅ Teo Bot успешно остановлен на инстансе $INSTANCE_NAME"
    log "💡 Для запуска бота используйте: ./scripts/start_teo.sh $INSTANCE_NAME"
else
    error "❌ Ошибка при остановке бота"
    exit 1
fi
