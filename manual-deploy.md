# Ручной деплой односообщенного интерфейса

## 🚀 **Пошаговая инструкция**

### 1. **Подключение к серверу**
```bash
# Подключитесь к серверу как root
ssh root@51.250.7.34
```

### 2. **Остановка существующего бота**
```bash
# Перейдите в директорию бота
cd /root/teo-bot

# Остановите Docker контейнер
docker-compose down

# Остановите systemd сервис
systemctl stop teo-bot.service
systemctl disable teo-bot.service

# Убейте все процессы Python
pkill -f 'python.*teo' || true
pkill -f 'python3.*teo' || true
```

### 3. **Создание резервной копии**
```bash
# Создайте резервную копию
tar -czf /tmp/teo_bot_backup_$(date +%Y%m%d_%H%M%S).tar.gz .
```

### 4. **Копирование файлов**

#### **На локальной машине:**
```bash
# Скопируйте файлы на сервер
scp -r src/ root@51.250.7.34:/root/teo-bot/
scp -r docs/ root@51.250.7.34:/root/teo-bot/
scp -r assets/ root@51.250.7.34:/root/teo-bot/
scp -r scripts/ root@51.250.7.34:/root/teo-bot/
scp requirements.txt root@51.250.7.34:/root/teo-bot/
scp Dockerfile root@51.250.7.34:/root/teo-bot/
scp docker-compose.yml root@51.250.7.34:/root/teo-bot/
scp README.md root@51.250.7.34:/root/teo-bot/
scp env_example root@51.250.7.34:/root/teo-bot/

# Скопируйте .env файл (если есть)
scp .env root@51.250.7.34:/root/teo-bot/
```

#### **На сервере:**
```bash
# Установите права доступа
chmod +x scripts/*.sh
chown -R root:root .
```

### 5. **Запуск миграции базы данных**
```bash
# Запустите миграцию
python3 -c "from src.database.migration import run_schema_migration; run_schema_migration()"
```

### 6. **Сборка и запуск**
```bash
# Соберите Docker образ
docker-compose build --no-cache

# Запустите контейнер
docker-compose up -d

# Проверьте статус
docker-compose ps

# Посмотрите логи
docker-compose logs --tail=20
```

### 7. **Проверка работы**
```bash
# Следите за логами
docker-compose logs -f
```

## 🔧 **Что изменилось в коде**

### **Новые функции:**
1. **Односообщенный интерфейс** - бот работает с одним главным сообщением
2. **Автоудаление** - входящие сообщения автоматически удаляются
3. **Состояния в БД** - текущее состояние сохраняется в базе данных
4. **KeyboardBuilder и MessageBuilder** - централизованные компоненты

### **Новые колонки в БД:**
```sql
ALTER TABLE users ADD COLUMN main_message_id INTEGER;
ALTER TABLE users ADD COLUMN current_state TEXT;
```

## 🧪 **Тестирование**

### **После деплоя:**
1. Найдите бота в Telegram
2. Отправьте команду `/start`
3. Проверьте навигацию по кнопкам
4. Попробуйте отправить текстовое сообщение (должно удалиться)
5. Проверьте все разделы: погода, привычки, настройки

### **Ожидаемое поведение:**
- ✅ Одно главное сообщение всегда видимо
- ✅ Входящие сообщения автоматически удаляются
- ✅ Навигация работает через кнопки
- ✅ Состояния сохраняются в БД

## 🐛 **Устранение проблем**

### **Если бот не запускается:**
```bash
# Проверьте логи
docker-compose logs

# Проверьте статус контейнера
docker-compose ps

# Перезапустите контейнер
docker-compose restart
```

### **Если есть ошибки в коде:**
```bash
# Проверьте синтаксис
python3 -m py_compile src/core/teo_bot.py

# Проверьте импорты
python3 -c "from src.utils.keyboards import KeyboardBuilder; print('OK')"
python3 -c "from src.utils.messages import MessageBuilder; print('OK')"
```

### **Если проблемы с БД:**
```bash
# Проверьте схему БД
sqlite3 data/teo_bot.db ".schema users"

# Запустите миграцию вручную
python3 -c "from src.database.migration import run_schema_migration; run_schema_migration()"
```

## 📞 **Полезные команды**

### **Мониторинг:**
```bash
# Логи в реальном времени
docker-compose logs -f

# Статус контейнера
docker-compose ps

# Использование ресурсов
docker stats
```

### **Управление:**
```bash
# Остановить бота
docker-compose down

# Запустить бота
docker-compose up -d

# Перезапустить бота
docker-compose restart
```

### **Отладка:**
```bash
# Войти в контейнер
docker-compose exec teo-bot bash

# Проверить файлы в контейнере
docker-compose exec teo-bot ls -la
```



