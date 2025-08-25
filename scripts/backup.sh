#!/bin/bash

# Скрипт для создания резервных копий Teo Bot
# Использование: ./backup.sh [instance-name]

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

log "Создаем резервную копию Teo Bot с инстанса: $INSTANCE_NAME"

# Проверяем существование инстанса
if ! yc compute instance get $INSTANCE_NAME &> /dev/null; then
    error "Инстанс $INSTANCE_NAME не найден!"
    exit 1
fi

# Получаем внешний IP адрес инстанса
INSTANCE_IP=$(yc compute instance get $INSTANCE_NAME --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')

log "IP адрес инстанса: $INSTANCE_IP"

# Создаем папку для бэкапов локально
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

log "Создаем резервную копию на сервере..."

# Создаем бэкап на сервере
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    cd /home/ubuntu/teo-bot
    
    # Создаем папку для бэкапов если её нет
    mkdir -p backups
    
    # Создаем бэкап базы данных
    if [ -f data/teo_bot.db ]; then
        cp data/teo_bot.db "backups/teo_bot_$(date +%Y%m%d_%H%M%S).db"
        echo "✅ Резервная копия базы данных создана"
    else
        echo "⚠️  База данных не найдена"
    fi
    
    # Создаем бэкап файла привычек
    if [ -f data/user_habits.json ]; then
        cp data/user_habits.json "backups/user_habits_$(date +%Y%m%d_%H%M%S).json"
        echo "✅ Резервная копия привычек создана"
    else
        echo "⚠️  Файл привычек не найден"
    fi
    
    # Создаем бэкап .env файла
    if [ -f .env ]; then
        cp .env "backups/env_$(date +%Y%m%d_%H%M%S).env"
        echo "✅ Резервная копия .env создана"
    else
        echo "⚠️  .env файл не найден"
    fi
    
    # Создаем архив всех бэкапов
    cd backups
    tar -czf "full_backup_$(date +%Y%m%d_%H%M%S).tar.gz" *.db *.json *.env 2>/dev/null || true
    echo "✅ Полный архив бэкапов создан"
EOF

# Копируем бэкапы с сервера
log "Копируем резервные копии с сервера..."
scp -o StrictHostKeyChecking=no -r ubuntu@$INSTANCE_IP:/home/ubuntu/teo-bot/backups/* "$BACKUP_DIR/"

# Создаем информацию о бэкапе
cat > "$BACKUP_DIR/backup_info.txt" << EOF
Резервная копия Teo Bot
Дата создания: $(date)
Инстанс: $INSTANCE_NAME
IP адрес: $INSTANCE_IP

Содержимое бэкапа:
$(ls -la "$BACKUP_DIR")

Для восстановления:
1. Остановите бота: ./update.sh $INSTANCE_NAME
2. Скопируйте нужные файлы обратно на сервер
3. Перезапустите бота: ./update.sh $INSTANCE_NAME
EOF

log "Резервная копия создана в папке: $BACKUP_DIR"
log "Информация о бэкапе сохранена в: $BACKUP_DIR/backup_info.txt"

# Показываем размер бэкапа
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Размер резервной копии: $BACKUP_SIZE"

# Очищаем старые бэкапы на сервере (оставляем последние 5)
log "Очищаем старые бэкапы на сервере..."
ssh -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
    cd /home/ubuntu/teo-bot/backups
    
    # Удаляем старые файлы базы данных (оставляем последние 5)
    ls -t teo_bot_*.db 2>/dev/null | tail -n +6 | xargs -r rm -f
    
    # Удаляем старые файлы привычек (оставляем последние 5)
    ls -t user_habits_*.json 2>/dev/null | tail -n +6 | xargs -r rm -f
    
    # Удаляем старые .env файлы (оставляем последние 5)
    ls -t env_*.env 2>/dev/null | tail -n +6 | xargs -r rm -f
    
    # Удаляем старые архивы (оставляем последние 3)
    ls -t full_backup_*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f
    
    echo "Старые бэкапы очищены"
EOF

log "Резервное копирование завершено!"
