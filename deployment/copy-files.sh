#!/bin/bash

# Simple file copy script
# Usage: ./copy-files.sh [SERVER_IP]

SERVER_IP=${1:-51.250.7.34}
REMOTE_DIR="/root/teo-bot"

echo "Копирование файлов на сервер $SERVER_IP..."

# Copy main directories
echo "Копируем src/..."
scp -r src/ root@$SERVER_IP:$REMOTE_DIR/

echo "Копируем docs/..."
scp -r docs/ root@$SERVER_IP:$REMOTE_DIR/

echo "Копируем assets/..."
scp -r assets/ root@$SERVER_IP:$REMOTE_DIR/

echo "Копируем scripts/..."
scp -r scripts/ root@$SERVER_IP:$REMOTE_DIR/

# Copy configuration files
echo "Копируем конфигурационные файлы..."
scp requirements.txt root@$SERVER_IP:$REMOTE_DIR/
scp Dockerfile root@$SERVER_IP:$REMOTE_DIR/
scp docker-compose.yml root@$SERVER_IP:$REMOTE_DIR/
scp README.md root@$SERVER_IP:$REMOTE_DIR/
scp env_example root@$SERVER_IP:$REMOTE_DIR/

# Copy environment file if exists
if [ -f .env ]; then
    echo "Копируем .env..."
    scp .env root@$SERVER_IP:$REMOTE_DIR/
else
    echo "Файл .env не найден"
fi

# Copy database if exists
if [ -f data/teo_bot.db ]; then
    echo "Копируем базу данных..."
    ssh root@$SERVER_IP "mkdir -p $REMOTE_DIR/data"
    scp data/teo_bot.db root@$SERVER_IP:$REMOTE_DIR/data/
else
    echo "База данных не найдена"
fi

echo "Копирование завершено!"
echo ""
echo "Теперь подключитесь к серверу и выполните:"
echo "ssh root@$SERVER_IP"
echo "cd $REMOTE_DIR"
echo "chmod +x scripts/*.sh"
echo "python3 -c \"from src.database.migration import run_schema_migration; run_schema_migration()\""
echo "docker-compose build --no-cache"
echo "docker-compose up -d"








