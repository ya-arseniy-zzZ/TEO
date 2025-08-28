# 🤖 Teo - Персональный Telegram Бот-Помощник

Teo - это умный Telegram бот, который помогает пользователям получать актуальную погоду, новости и отслеживать привычки.

## 📁 Структура проекта

```
TEO/
├── app/                    # Основное приложение
│   ├── core/              # Основные компоненты
│   │   ├── main.py        # Точка входа
│   │   └── teo_bot.py     # Основной класс бота
│   ├── services/          # Сервисы
│   │   ├── weather_service.py      # Сервис погоды
│   │   ├── news_service.py         # Сервис новостей
│   │   ├── habit_tracker.py        # Трекер привычек
│   │   ├── notification_scheduler.py # Планировщик уведомлений
│   │   ├── rain_monitor.py         # Мониторинг дождя
│   │   └── finance_service.py      # Сервис финансового анализа
│   ├── database/          # Работа с базой данных
│   │   ├── database.py    # Менеджер БД
│   │   └── migration.py   # Миграции
│   ├── interfaces/        # Интерфейсы
│   │   ├── habit_interface.py      # Интерфейс привычек
│   │   ├── news_interface.py       # Интерфейс новостей
│   │   ├── finance_interface.py    # Интерфейс финансового анализа
│   │   └── interactive_settings.py # Интерактивные настройки
│   └── utils/             # Утилиты
│       ├── config.py      # Конфигурация
│       └── habit_methods.py # Методы для привычек
├── config/                # Конфигурация
│   ├── requirements.txt   # Python зависимости
│   └── env_example        # Пример переменных окружения
├── scripts/               # Скрипты запуска
├── tests/                 # Тесты
├── deployment/            # Файлы деплоя
│   ├── Dockerfile         # Docker конфигурация
│   ├── docker-compose.yml # Docker Compose
│   └── *.sh              # Скрипты деплоя
├── docs/                  # Документация
├── assets/                # Медиафайлы
├── data/                  # Данные
│   ├── teo_bot.db        # База данных SQLite
│   └── user_habits.json  # Файл привычек
├── backups/               # Резервные копии
├── run.py                 # Основной скрипт запуска
└── run_anchor.py          # Скрипт запуска Anchor UX
```

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repository-url>
cd TEO
cp config/env_example .env
# Отредактируйте .env файл с вашими токенами
```

### 2. Установка зависимостей

```bash
pip install -r config/requirements.txt
```

### 3. Запуск бота

```bash
# Основной запуск
python3 run.py

# Запуск с Anchor UX
python3 run_anchor.py

# Или используйте скрипты
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

### 💰 Финансы
- Интеграция с Google Sheets
- Анализ доходов и расходов
- Категоризация трат
- Статистика по периодам
- Цели и достижения

## 🛠 Разработка

### Структура кода

- **`app/core/`** - Основные компоненты бота
- **`app/services/`** - Бизнес-логика и внешние API
- **`app/database/`** - Работа с данными
- **`app/interfaces/`** - Пользовательские интерфейсы
- **`app/utils/`** - Вспомогательные функции

### Добавление новых функций

1. Создайте новый сервис в `app/services/`
2. Добавьте интерфейс в `app/interfaces/` если нужен UI
3. Обновите `app/core/teo_bot.py` для интеграции
4. Добавьте тесты и документацию

## 📦 Деплой

### Docker

```bash
cd deployment
docker build -t teo-bot .
docker run -d --name teo-bot teo-bot
```

### Docker Compose

```bash
cd deployment
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
