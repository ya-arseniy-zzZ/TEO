#!/bin/bash

# Скрипт для деплоя Teo Bot на Яндекс.Облако
# Использование: ./deploy.sh [instance-name]

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

# Проверяем наличие Yandex CLI
if ! command -v yc &> /dev/null; then
    error "Yandex CLI не установлен. Установите его: https://cloud.yandex.ru/docs/cli/quickstart"
    exit 1
fi

# Проверяем авторизацию
if ! yc config list &> /dev/null; then
    error "Не авторизован в Yandex CLI. Выполните: yc init"
    exit 1
fi

# Получаем имя инстанса из аргумента или используем по умолчанию
INSTANCE_NAME=${1:-"teo-bot-instance"}

log "Начинаем деплой Teo Bot на инстанс: $INSTANCE_NAME"

# Проверяем существование инстанса
if yc compute instance get $INSTANCE_NAME &> /dev/null; then
    log "Инстанс $INSTANCE_NAME уже существует"
    
    # Запускаем инстанс если он остановлен
    INSTANCE_STATUS=$(yc compute instance get $INSTANCE_NAME --format=json | jq -r '.status')
    if [ "$INSTANCE_STATUS" != "RUNNING" ]; then
        log "Запускаем инстанс..."
        yc compute instance start $INSTANCE_NAME
        sleep 30
    fi
else
    log "Создаем новый инстанс $INSTANCE_NAME..."
    
    # Создаем инстанс
    yc compute instance create \
        --name $INSTANCE_NAME \
        --zone ru-central1-a \
        --platform standard-v2 \
        --cores 2 \
        --memory 4GB \
        --network-interface subnet-name=default-ru-central1-a,ipv4-address=auto,nat-ip-version=ipv4 \
        --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2004-lts,size=20GB \
        --metadata serial-port-enable=0 \
        --metadata ssh-keys="ubuntu:$(cat ~/.ssh/id_rsa.pub)"
fi

# Получаем внешний IP адрес инстанса
INSTANCE_IP=$(yc compute instance get $INSTANCE_NAME --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')

log "IP адрес инстанса: $INSTANCE_IP"

# Ждем пока инстанс будет готов
log "Ждем готовности инстанса..."
sleep 30

# Создаем временную папку без git
log "Подготавливаем файлы для копирования..."
TEMP_DIR=$(mktemp -d)
cp -r * "$TEMP_DIR/"
cp .env "$TEMP_DIR/" 2>/dev/null || true

# Копируем файлы проекта
log "Копируем файлы проекта..."
scp -o StrictHostKeyChecking=no -r "$TEMP_DIR"/* ubuntu@$INSTANCE_IP:/home/ubuntu/

# Очищаем временную папку
rm -rf "$TEMP_DIR"

# Подключаемся к инстансу и настраиваем окружение
log "Настраиваем окружение на инстансе..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    cd /home/ubuntu
    
    # Создаем папку teo-bot и перемещаем файлы
    mkdir -p teo-bot
    mv src assets data scripts docs Dockerfile docker-compose.yml requirements.txt env_example .dockerignore teo-bot/ 2>/dev/null || true
    cd teo-bot
    
    # Обновляем систему
    sudo apt update && sudo apt upgrade -y
    
    # Устанавливаем Docker
    if ! command -v docker &> /dev/null; then
        # Устанавливаем Docker вручную для Ubuntu 20.04
        sudo apt-get update
        sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io
        sudo usermod -aG docker ubuntu
        sudo systemctl enable docker
        sudo systemctl start docker
    fi
    
    # Устанавливаем Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    
    # Создаем .env файл если его нет
    if [ ! -f .env ]; then
        if [ -f env_example ]; then
            cp env_example .env
            echo "⚠️  ВНИМАНИЕ: Создан файл .env из примера. Отредактируйте его с вашими токенами!"
        else
            echo "⚠️  Файл env_example не найден. Создайте .env файл вручную!"
        fi
    fi
    
    # Создаем systemd сервис для автозапуска
    sudo tee /etc/systemd/system/teo-bot.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Teo Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/teo-bot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    # Включаем автозапуск сервиса
    sudo systemctl enable teo-bot.service
    
    # Запускаем бота
    sudo systemctl start teo-bot.service
    
    # Проверяем статус
    sudo systemctl status teo-bot.service
EOF

log "Деплой завершен!"
log "Для просмотра логов выполните: ssh ubuntu@$INSTANCE_IP 'sudo journalctl -u teo-bot.service -f'"
log "Для остановки бота: ssh ubuntu@$INSTANCE_IP 'sudo systemctl stop teo-bot.service'"
log "Для запуска бота: ssh ubuntu@$INSTANCE_IP 'sudo systemctl start teo-bot.service'"
