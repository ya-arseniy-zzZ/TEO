# 🤖 Teo - Персональный Telegram Бот-Помощник

Teo - это умный Telegram бот, который помогает пользователям получать актуальную погоду, новости и отслеживать привычки.

## 📁 Структура проекта

```
TEO/
├── src/                    # Исходный код
│   ├── core/              # Основные компоненты
│   │   ├── main.py        # Точка входа
│   │   └── teo_bot.py     # Основной класс бота
│   ├── services/          # Сервисы
│   │   ├── weather_service.py      # Сервис погоды
│   │   ├── news_service.py         # Сервис новостей
│   │   ├── habit_tracker.py        # Трекер привычек
│   │   ├── notification_scheduler.py # Планировщик уведомлений
│   │   └── rain_monitor.py         # Мониторинг дождя
│   ├── database/          # Работа с базой данных
│   │   ├── database.py    # Менеджер БД
│   │   └── migration.py   # Миграции
│   ├── interfaces/        # Интерфейсы
│   │   ├── habit_interface.py      # Интерфейс привычек
│   │   ├── news_interface.py       # Интерфейс новостей
│   │   └── interactive_settings.py # Интерактивные настройки
│   └── utils/             # Утилиты
│       ├── config.py      # Конфигурация
│       └── habit_methods.py # Методы для привычек
├── assets/                # Медиафайлы
│   ├── bot_avatar.jpg
│   ├── bot_avatar_for_news.jpeg
│   ├── bot_avatar_for_start.jpeg
│   └── bot_avatar_for_weather.jpg
├── data/                  # Данные
│   ├── teo_bot.db        # База данных SQLite
│   └── user_habits.json  # Файл привычек
├── scripts/              # Скрипты
│   ├── start_teo.sh      # Запуск бота
│   ├── backup.sh         # Резервное копирование
│   ├── deploy.sh         # Деплой
│   ├── monitor.sh        # Мониторинг
│   └── update.sh         # Обновление
├── docs/                 # Документация
│   ├── README.md
│   ├── README_DEPLOY.md
│   ├── deploy-manual.md
│   └── QUICK_START.md
├── Dockerfile            # Docker конфигурация
├── docker-compose.yml    # Docker Compose
├── requirements.txt      # Python зависимости
├── env_example          # Пример переменных окружения
└── .gitignore           # Git ignore
```

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repository-url>
cd TEO
cp env_example .env
# Отредактируйте .env файл с вашими токенами
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Запуск бота

```bash
# Простой запуск
python3 src/core/main.py

# Или используйте скрипт
chmod +x scripts/start_teo.sh
./scripts/start_teo.sh
```

## 🔧 Основные функции

### 🌤 Погода
- Текущая погода в любом городе
- Прогноз на 3 дня
- Уведомления о дожде
- Настраиваемые параметры

### 📰 Новости
- Последние новости России
- Категории новостей
- Поиск по ключевым словам
- Сохранение избранных новостей

### 🎯 Привычки
- Создание и отслеживание привычек
- Статистика выполнения
- Напоминания
- Цели и достижения

## 🛠 Разработка

### Структура кода

- **`src/core/`** - Основные компоненты бота
- **`src/services/`** - Бизнес-логика и внешние API
- **`src/database/`** - Работа с данными
- **`src/interfaces/`** - Пользовательские интерфейсы
- **`src/utils/`** - Вспомогательные функции

### Добавление новых функций

1. Создайте новый сервис в `src/services/`
2. Добавьте интерфейс в `src/interfaces/` если нужен UI
3. Обновите `src/core/teo_bot.py` для интеграции
4. Добавьте тесты и документацию

## 📦 Деплой

### Docker

```bash
docker build -t teo-bot .
docker run -d --name teo-bot teo-bot
```

### Docker Compose

```bash
docker-compose up -d
```

### Ручной деплой

См. `docs/README_DEPLOY.md` для подробных инструкций.

## 🔄 Резервное копирование

```bash
./scripts/backup.sh [instance-name]
```

## 📊 Мониторинг

```bash
./scripts/monitor.sh [instance-name]
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

MIT License

## 📞 Поддержка

Если у вас есть вопросы или проблемы, создайте Issue в репозитории.
