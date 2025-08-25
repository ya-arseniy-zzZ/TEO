# Инструкция по деплою Teo Bot в облако

## Подготовка

### 1. Установка CLI (опционально)
```bash
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
exec -l $SHELL
```

### 2. Авторизация в облаке
```bash
yc init
```

### 3. Создание SSH ключей (если нет)
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
```

## Автоматический деплой

### Быстрый запуск
```bash
chmod +x deploy.sh
./deploy.sh [имя-инстанса]
```

## Ручной деплой

### 1. Создание Compute Instance

```bash
# Создаем инстанс
yc compute instance create \
    --name teo-bot-instance \
    --zone ru-central1-a \
    --platform standard-v2 \
    --cores 2 \
    --memory 4GB \
    --network-interface subnet-name=default-ru-central1-a,ipv4-address=auto,nat-ip-version=ipv4 \
    --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2004-lts,size=20GB \
    --metadata serial-port-enable=0 \
    --metadata ssh-keys="ubuntu:$(cat ~/.ssh/id_rsa.pub)"
```

### 2. Получение IP адреса
```bash
yc compute instance get teo-bot-instance --format=json | jq -r '.network_interfaces[0].primary_v4_address.address'
```

### 3. Подключение к инстансу
```bash
ssh ubuntu@[IP-АДРЕС]
```

### 4. Установка Docker и Docker Compose
```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
rm get-docker.sh

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагружаемся для применения изменений группы
sudo reboot
```

### 5. Копирование проекта
```bash
# На локальной машине
scp -r . ubuntu@[IP-АДРЕС]:/home/ubuntu/teo-bot/
```

### 6. Настройка окружения
```bash
# Подключаемся к инстансу
ssh ubuntu@[IP-АДРЕС]

cd /home/ubuntu/teo-bot

# Создаем .env файл
cp env_example .env
nano .env  # Редактируем с вашими токенами
```

### 7. Запуск бота
```bash
# Запускаем через Docker Compose
docker-compose up -d

# Проверяем статус
docker-compose ps
docker-compose logs -f
```

### 8. Настройка автозапуска
```bash
# Создаем systemd сервис
sudo tee /etc/systemd/system/teo-bot.service > /dev/null << 'EOF'
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
EOF

# Включаем автозапуск
sudo systemctl enable teo-bot.service
sudo systemctl start teo-bot.service
```

## Управление ботом

### Просмотр логов
```bash
# Логи Docker контейнера
docker-compose logs -f

# Логи systemd сервиса
sudo journalctl -u teo-bot.service -f
```

### Остановка/Запуск
```bash
# Через Docker Compose
docker-compose down
docker-compose up -d

# Через systemd
sudo systemctl stop teo-bot.service
sudo systemctl start teo-bot.service
```

### Обновление бота
```bash
# Останавливаем
docker-compose down

# Копируем новые файлы
scp -r . ubuntu@[IP-АДРЕС]:/home/ubuntu/teo-bot/

# Пересобираем и запускаем
docker-compose up -d --build
```

## Мониторинг

### Проверка статуса
```bash
# Статус сервиса
sudo systemctl status teo-bot.service

# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats
```

### Настройка мониторинга
Можно добавить Prometheus и Grafana для более детального мониторинга.

## Безопасность

### Firewall
```bash
# Открываем только SSH порт
sudo ufw allow ssh
sudo ufw enable
```

### Обновления
```bash
# Автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Резервное копирование

### База данных
```bash
# Создание бэкапа
docker-compose exec teo-bot sqlite3 teo_bot.db ".backup '/backup/teo_bot_$(date +%Y%m%d_%H%M%S).db'"

# Восстановление
docker-compose exec teo-bot sqlite3 teo_bot.db ".restore '/backup/teo_bot_YYYYMMDD_HHMMSS.db'"
```

## Устранение неполадок

### Проверка логов
```bash
# Логи приложения
docker-compose logs teo-bot

# Логи системы
sudo journalctl -u teo-bot.service -n 100

# Проверка переменных окружения
docker-compose exec teo-bot env | grep -E "(TELEGRAM|WEATHER|CITY|TIMEZONE)"
```

### Перезапуск с нуля
```bash
# Полная перезагрузка
docker-compose down
docker system prune -f
docker-compose up -d --build
```
