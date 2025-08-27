#!/bin/bash

# Скрипт для обновления Teo Bot на TimeWeb сервере
# Использование: ./update-server.sh

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

SERVER_IP="62.113.36.171"

log "Начинаем обновление Teo Bot на сервере: $SERVER_IP"

# Проверяем SSH подключение
log "Проверяем подключение к серверу..."
if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@$SERVER_IP 'echo "SSH подключение работает"' 2>/dev/null; then
    error "Не удается подключиться к серверу $SERVER_IP"
    exit 1
fi

# Создаем резервную копию на сервере
log "Создаем резервную копию на сервере..."
ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'EOF'
    cd /root/teo-bot
    
    # Создаем папку для бэкапов если её нет
    mkdir -p backups
    
    # Создаем бэкап базы данных
    if [ -f data/teo_bot.db ]; then
        cp data/teo_bot.db "backups/teo_bot_$(date +%Y%m%d_%H%M%S).db"
        echo "✅ Резервная копия базы данных создана"
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
ssh -o StrictHostKeyChecking=no root@$SERVER_IP 'systemctl stop teo-bot.service'

# Создаем временную папку без git
log "Подготавливаем файлы для копирования..."
TEMP_DIR=$(mktemp -d)
cp -r * "$TEMP_DIR/"
cp .env "$TEMP_DIR/" 2>/dev/null || true

# Копируем новые файлы проекта
log "Копируем новые файлы проекта..."
scp -o StrictHostKeyChecking=no -r "$TEMP_DIR"/* root@$SERVER_IP:/root/teo-bot-new/

# Очищаем временную папку
rm -rf "$TEMP_DIR"

# Обновляем проект на сервере
log "Обновляем проект на сервере..."
ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'EOF'
    cd /root
    
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
ssh -o StrictHostKeyChecking=no root@$SERVER_IP 'systemctl start teo-bot.service'

# Проверяем статус
log "Проверяем статус обновления..."
ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'EOF'
    echo "=== Статус systemd сервиса ==="
    systemctl status teo-bot.service --no-pager
    
    echo -e "\n=== Статус Docker контейнеров ==="
    cd /root/teo-bot
    docker-compose ps
    
    echo -e "\n=== Последние логи ==="
    docker-compose logs --tail=20
EOF

log "Обновление завершено!"
log "Для просмотра логов: ssh root@$SERVER_IP 'cd /root/teo-bot && docker-compose logs -f'"
log "Для проверки статуса: ssh root@$SERVER_IP 'systemctl status teo-bot.service'"






