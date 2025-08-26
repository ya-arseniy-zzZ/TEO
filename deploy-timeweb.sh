#!/bin/bash

# Скрипт для деплоя Teo Bot на Timeweb VPS
# Использование: ./deploy-timeweb.sh [IP-АДРЕС-СЕРВЕРА]

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

# Проверяем аргументы
if [ $# -eq 0 ]; then
    error "Укажите IP адрес сервера!"
    echo "Использование: ./deploy-timeweb.sh [IP-АДРЕС-СЕРВЕРА]"
    echo ""
    echo "Примеры дешевых VPS:"
    echo "  Timeweb: от 150₽/месяц"
    echo "  Beget: от 200₽/месяц"
    echo "  Reg.ru: от 180₽/месяц"
    exit 1
fi

SERVER_IP=$1

log "Начинаем деплой Teo Bot на сервер: $SERVER_IP"

# Проверяем SSH подключение
log "Проверяем подключение к серверу..."
if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@$SERVER_IP 'echo "SSH подключение работает"' 2>/dev/null; then
    error "Не удается подключиться к серверу $SERVER_IP"
    echo "Убедитесь что:"
    echo "1. Сервер запущен"
    echo "2. SSH доступен на порту 22"
    echo "3. SSH ключи настроены правильно"
    exit 1
fi

# Создаем временную папку без git
log "Подготавливаем файлы для копирования..."
TEMP_DIR=$(mktemp -d)
cp -r * "$TEMP_DIR/"
cp .env "$TEMP_DIR/" 2>/dev/null || true

# Копируем файлы проекта
log "Копируем файлы проекта на сервер..."
scp -o StrictHostKeyChecking=no -r "$TEMP_DIR"/* root@$SERVER_IP:/root/teo-bot/

# Очищаем временную папку
rm -rf "$TEMP_DIR"

# Настраиваем сервер
log "Настраиваем окружение на сервере..."
ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'EOF'
    cd /root/teo-bot
    
    # Обновляем систему
    apt update && apt upgrade -y
    
    # Устанавливаем Python и pip
    apt install -y python3 python3-pip python3-venv
    
    # Устанавливаем Docker
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
    fi
    
    # Устанавливаем Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    
    # Создаем .env файл если его нет
    if [ ! -f .env ]; then
        if [ -f env_example ]; then
            cp env_example .env
            echo "⚠️  Создан файл .env из примера. Отредактируйте его с вашими токенами!"
        else
            echo "⚠️  Файл env_example не найден. Создайте .env файл вручную!"
        fi
    fi
    
    # Создаем systemd сервис
    cat > /etc/systemd/system/teo-bot.service << 'SERVICE_EOF'
[Unit]
Description=Teo Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/teo-bot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    # Включаем автозапуск сервиса
    systemctl enable teo-bot.service
    
    # Запускаем бота
    systemctl start teo-bot.service
    
    # Проверяем статус
    systemctl status teo-bot.service
EOF

log "Деплой завершен!"
log "Для просмотра логов: ssh root@$SERVER_IP 'cd teo-bot && docker-compose logs -f'"
log "Для остановки бота: ssh root@$SERVER_IP 'systemctl stop teo-bot.service'"
log "Для запуска бота: ssh root@$SERVER_IP 'systemctl start teo-bot.service'"



