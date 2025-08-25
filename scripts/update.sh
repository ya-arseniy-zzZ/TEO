#!/bin/bash

# Скрипт для обновления Teo Bot на сервере
# Использование: ./update.sh [instance-name]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Получаем имя инстанса из аргумента или используем по умолчанию
INSTANCE_NAME=${1:-"teo-bot-instance"}

log "Начинаем обновление Teo Bot на инстансе: $INSTANCE_NAME"

# Проверяем существование инстанса
if ! yc compute instance get $INSTANCE_NAME &> /dev/null; then
    error "Инстанс $INSTANCE_NAME не найден!"
    exit 1
fi

# Получаем внешний IP адрес инстанса
INSTANCE_IP=$(yc compute instance get $INSTANCE_NAME --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')

log "IP адрес инстанса: $INSTANCE_IP"

# Создаем резервную копию базы данных
log "Создаем резервную копию базы данных..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    cd /home/ubuntu/teo-bot
    
    # Создаем папку для бэкапов если её нет
    mkdir -p backups
    
    # Создаем бэкап базы данных
    if [ -f data/teo_bot.db ]; then
        cp data/teo_bot.db "backups/teo_bot_$(date +%Y%m%d_%H%M%S).db"
        echo "✅ Резервная копия создана"
    else
        echo "⚠️  База данных не найдена, пропускаем бэкап"
    fi
    
    # Создаем бэкап файла привычек
    if [ -f data/user_habits.json ]; then
        cp data/user_habits.json "backups/user_habits_$(date +%Y%m%d_%H%M%S).json"
        echo "✅ Резервная копия привычек создана"
    fi
EOF

# Останавливаем бота
log "Останавливаем бота..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP 'sudo systemctl stop teo-bot.service'

# Копируем новые файлы проекта
log "Копируем новые файлы проекта..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP 'mkdir -p /home/ubuntu/teo-bot-new'
scp -o StrictHostKeyChecking=no -r . ubuntu@$INSTANCE_IP:/home/ubuntu/teo-bot-new/

# Обновляем проект на сервере
log "Обновляем проект на сервере..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    cd /home/ubuntu
    
    # Останавливаем старые контейнеры
    if [ -d teo-bot ]; then
        cd teo-bot
        docker-compose down 2>/dev/null || true
        cd ..
    fi
    
    # Удаляем старую папку и переименовываем новую
    rm -rf teo-bot
    mv teo-bot-new teo-bot
    
    cd teo-bot
    
    # Восстанавливаем .env файл если он был
    if [ ! -f .env ]; then
        if [ -f env_example ]; then
            cp env_example .env
            echo "⚠️  Создан новый .env файл из примера. Проверьте настройки!"
        fi
    fi
    
    # Пересобираем и запускаем контейнеры
    docker-compose down 2>/dev/null || true
    docker-compose build --no-cache
    docker-compose up -d
    
    # Проверяем статус
    sleep 5
    docker-compose ps
EOF

# Запускаем бота
log "Запускаем обновленного бота..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP 'sudo systemctl start teo-bot.service'

# Проверяем статус
log "Проверяем статус обновления..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    echo "=== Статус systemd сервиса ==="
    sudo systemctl status teo-bot.service --no-pager
    
    echo -e "\n=== Статус Docker контейнеров ==="
    docker-compose ps
    
    echo -e "\n=== Последние логи ==="
    docker-compose logs --tail=20
EOF

log "Обновление завершено!"
log "Для просмотра логов: ssh ubuntu@$INSTANCE_IP 'docker-compose logs -f'"
log "Для проверки статуса: ssh ubuntu@$INSTANCE_IP 'sudo systemctl status teo-bot.service'"
