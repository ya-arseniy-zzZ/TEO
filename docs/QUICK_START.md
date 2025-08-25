# 🚀 Быстрый запуск Teo Bot в облаке

## Предварительные требования

1. **Аккаунт в облачном провайдере** (AWS, Google Cloud, Azure, или любой VPS)
2. **Сервисный аккаунт** с правами на создание Compute Instance
3. **SSH ключи** на локальной машине

## Шаг 1: Подготовка

### Установка CLI (опционально)
```bash
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
exec -l $SHELL
```

### Авторизация
```bash
yc init
```

### Создание SSH ключей (если нет)
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
```

## Шаг 2: Настройка токенов

Отредактируйте файл `.env` с вашими токенами:
```bash
cp env_example .env
nano .env
```

**Обязательные переменные:**
- `TELEGRAM_BOT_TOKEN` - токен от @BotFather
- `WEATHER_API_KEY` - ключ от OpenWeatherMap
- `DEFAULT_CITY` - ваш город
- `TIMEZONE` - ваш часовой пояс

## Шаг 3: Автоматический деплой

```bash
./deploy.sh [имя-инстанса]
```

**Пример:**
```bash
./deploy.sh my-teo-bot
```

## Шаг 4: Проверка работы

```bash
./monitor.sh [имя-инстанса]
```

## Управление ботом

### Обновление
```bash
./update.sh [имя-инстанса]
```

### Мониторинг
```bash
./monitor.sh [имя-инстанса]
```

### Просмотр логов
```bash
# Получить IP инстанса
yc compute instance get [имя-инстанса] --format=json | jq -r '.network_interfaces[0].primary_v4_address.address'

# Подключиться и посмотреть логи
ssh ubuntu@[IP-АДРЕС] 'docker-compose logs -f'
```

## Стоимость

Примерная стоимость в месяц:
- **Compute Instance** (2 vCPU, 4GB RAM): ~500-800 ₽
- **Диск** (20GB): ~50-100 ₽
- **Исходящий трафик**: зависит от использования

**Итого: ~600-1000 ₽/месяц**

## Устранение проблем

### Бот не отвечает
1. Проверьте статус: `./monitor.sh [имя-инстанса]`
2. Проверьте токены в `.env`
3. Посмотрите логи: `ssh ubuntu@[IP] 'docker-compose logs'`

### Ошибки деплоя
1. Проверьте авторизацию: `yc config list`
2. Проверьте SSH ключи: `ls -la ~/.ssh/id_rsa.pub`
3. Проверьте баланс в вашем облачном аккаунте

### Обновление не работает
1. Остановите инстанс: `yc compute instance stop [имя-инстанса]`
2. Запустите заново: `yc compute instance start [имя-инстанса]`
3. Повторите деплой: `./deploy.sh [имя-инстанса]`

## Полезные команды

```bash
# Остановить инстанс
yc compute instance stop [имя-инстанса]

# Запустить инстанс
yc compute instance start [имя-инстанса]

# Удалить инстанс (осторожно!)
yc compute instance delete [имя-инстанса]

# Посмотреть все инстансы
yc compute instance list
```

## Поддержка

При возникновении проблем:
1. Проверьте логи: `./monitor.sh [имя-инстанса]`
2. Убедитесь в правильности токенов
3. Проверьте баланс в вашем облачном аккаунте
4. Обратитесь к документации в `deploy-manual.md`
