#!/bin/bash

# Deploy script for root user
# Usage: ./deploy-root.sh [SERVER_IP]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if IP address is provided
if [ $# -eq 0 ]; then
    print_error "Укажите IP адрес сервера!"
    echo "Использование: $0 [IP-АДРЕС-СЕРВЕРА]"
    echo ""
    echo "Примеры дешевых VPS:"
    echo "  Timeweb: от 150₽/месяц"
    echo "  Beget: от 200₽/месяц"
    echo "  Reg.ru: от 180₽/месяц"
    exit 1
fi

SERVER_IP=$1
REMOTE_DIR="/root/teo-bot"

print_status "Начинаем деплой Teo Bot на сервер: $SERVER_IP"
print_status "Проверяем подключение к серверу..."

# Test SSH connection
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes root@$SERVER_IP "echo 'SSH connection test'" 2>/dev/null; then
    print_error "Не удается подключиться к серверу $SERVER_IP"
    echo "Убедитесь что:"
    echo "1. Сервер запущен"
    echo "2. SSH доступен на порту 22"
    echo "3. SSH ключи настроены правильно"
    echo ""
    echo "Попробуйте подключиться вручную:"
    echo "ssh root@$SERVER_IP"
    exit 1
fi

print_status "SSH подключение успешно!"

# Create backup
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

print_status "Создаем резервную копию..."

# Backup current files
if ssh root@$SERVER_IP "[ -d $REMOTE_DIR ]"; then
    ssh root@$SERVER_IP "cd $REMOTE_DIR && tar -czf /tmp/teo_bot_backup_$(date +%Y%m%d_%H%M%S).tar.gz ." || true
    scp root@$SERVER_IP:/tmp/teo_bot_backup_*.tar.gz "$BACKUP_DIR/" || true
    print_status "Резервная копия создана в $BACKUP_DIR"
else
    print_warning "Удаленная директория не найдена, пропускаем резервную копию"
fi

# Stop existing bot
print_status "Останавливаем существующего бота..."
ssh root@$SERVER_IP "cd $REMOTE_DIR && docker-compose down" || true
ssh root@$SERVER_IP "systemctl stop teo-bot.service" || true
ssh root@$SERVER_IP "systemctl disable teo-bot.service" || true

# Kill any remaining Python processes
print_status "Останавливаем все процессы Python..."
ssh root@$SERVER_IP "pkill -f 'python.*teo' || true"
ssh root@$SERVER_IP "pkill -f 'python3.*teo' || true"

# Create remote directory
print_status "Создаем удаленную директорию..."
ssh root@$SERVER_IP "mkdir -p $REMOTE_DIR"

# Copy files
print_status "Копируем файлы на сервер..."

# Copy main files
scp -r src/ root@$SERVER_IP:$REMOTE_DIR/
scp -r docs/ root@$SERVER_IP:$REMOTE_DIR/
scp -r assets/ root@$SERVER_IP:$REMOTE_DIR/
scp -r scripts/ root@$SERVER_IP:$REMOTE_DIR/

# Copy configuration files
scp requirements.txt root@$SERVER_IP:$REMOTE_DIR/
scp Dockerfile root@$SERVER_IP:$REMOTE_DIR/
scp docker-compose.yml root@$SERVER_IP:$REMOTE_DIR/
scp README.md root@$SERVER_IP:$REMOTE_DIR/
scp env_example root@$SERVER_IP:$REMOTE_DIR/

# Copy environment file if exists
if [ -f .env ]; then
    scp .env root@$SERVER_IP:$REMOTE_DIR/
    print_status "Файл .env скопирован"
else
    print_warning "Файл .env не найден, создайте его на сервере"
fi

# Create data directory and copy database if exists
print_status "Настраиваем базу данных..."
ssh root@$SERVER_IP "mkdir -p $REMOTE_DIR/data"
if [ -f data/teo_bot.db ]; then
    scp data/teo_bot.db root@$SERVER_IP:$REMOTE_DIR/data/
    print_status "База данных скопирована"
else
    print_warning "База данных не найдена, будет создана автоматически"
fi

# Set permissions
print_status "Устанавливаем права доступа..."
ssh root@$SERVER_IP "chmod +x $REMOTE_DIR/scripts/*.sh"
ssh root@$SERVER_IP "chown -R root:root $REMOTE_DIR"

# Run database migration
print_status "Запускаем миграцию базы данных..."
ssh root@$SERVER_IP "cd $REMOTE_DIR && python3 -c \"from src.database.migration import run_schema_migration; run_schema_migration()\"" || true

# Build and start Docker container
print_status "Собираем и запускаем Docker контейнер..."
ssh root@$SERVER_IP "cd $REMOTE_DIR && docker-compose build --no-cache"
ssh root@$SERVER_IP "cd $REMOTE_DIR && docker-compose up -d"

# Wait for container to start
print_status "Ждем запуска контейнера..."
sleep 10

# Check if container is running
if ssh root@$SERVER_IP "cd $REMOTE_DIR && docker-compose ps | grep -q 'Up'"; then
    print_status "✅ Контейнер успешно запущен!"
else
    print_error "❌ Контейнер не запустился"
    print_status "Проверяем логи..."
    ssh root@$SERVER_IP "cd $REMOTE_DIR && docker-compose logs"
    exit 1
fi

# Show logs
print_status "Показываем логи бота..."
ssh root@$SERVER_IP "cd $REMOTE_DIR && docker-compose logs --tail=20"

print_status "🎉 Деплой завершен успешно!"
print_status "Бот доступен по адресу: $SERVER_IP"
print_status "Для просмотра логов: ssh root@$SERVER_IP 'cd $REMOTE_DIR && docker-compose logs -f'"
print_status "Для остановки: ssh root@$SERVER_IP 'cd $REMOTE_DIR && docker-compose down'"


