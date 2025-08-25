# 📋 Заметки о миграции структуры проекта

## 🔄 Что было изменено

### 1. Реорганизация файлов по папкам

**Было:**
```
TEO/
├── main.py
├── teo_bot.py
├── config.py
├── database.py
├── weather_service.py
├── news_service.py
├── habit_tracker.py
├── habit_interface.py
├── habit_methods.py
├── news_interface.py
├── interactive_settings.py
├── notification_scheduler.py
├── rain_monitor.py
├── migration.py
├── *.jpeg, *.jpg
├── *.sh
├── *.md
├── teo_bot.db
├── user_habits.json
└── ...
```

**Стало:**
```
TEO/
├── src/
│   ├── core/              # main.py, teo_bot.py
│   ├── services/          # weather, news, habits, notifications
│   ├── database/          # database.py, migration.py
│   ├── interfaces/        # UI components
│   └── utils/             # config.py, habit_methods.py
├── assets/                # Все изображения
├── data/                  # База данных и JSON файлы
├── scripts/               # Все .sh файлы
└── docs/                  # Вся документация
```

### 2. Обновленные импорты

Все импорты были обновлены для работы с новой структурой:

```python
# Было:
from config import BOT_TOKEN
from weather_service import WeatherService
from database import DatabaseManager

# Стало:
from src.utils.config import BOT_TOKEN
from src.services.weather_service import WeatherService
from src.database.database import DatabaseManager
```

### 3. Обновленные пути к файлам

- **Изображения:** `bot_avatar.jpg` → `assets/bot_avatar.jpg`
- **База данных:** `teo_bot.db` → `data/teo_bot.db`
- **Привычки:** `user_habits.json` → `data/user_habits.json`

### 4. Обновленные скрипты

- **start_teo.sh:** `python3 main.py` → `python3 src/core/main.py`
- **Dockerfile:** `CMD ["python3", "main.py"]` → `CMD ["python3", "src/core/main.py"]`
- **backup.sh:** Обновлены пути к файлам данных

## ✅ Что проверено

1. ✅ Все Python файлы компилируются без ошибок
2. ✅ Все импорты работают корректно
3. ✅ Пути к файлам обновлены
4. ✅ Скрипты обновлены
5. ✅ Docker конфигурация обновлена

## 🚀 Как запускать после миграции

### Локальный запуск:
```bash
python3 src/core/main.py
```

### Через скрипт:
```bash
./scripts/start_teo.sh
```

### Docker:
```bash
docker build -t teo-bot .
docker run -d --name teo-bot teo-bot
```

## 📝 Преимущества новой структуры

1. **Лучшая организация:** Код разделен по функциональности
2. **Масштабируемость:** Легко добавлять новые модули
3. **Читаемость:** Понятная структура для новых разработчиков
4. **Изоляция:** Разделение данных, кода и ресурсов
5. **Стандарты:** Соответствует Python best practices

## 🔧 Для разработчиков

При добавлении новых функций:

1. **Сервисы** → `src/services/`
2. **Интерфейсы** → `src/interfaces/`
3. **Утилиты** → `src/utils/`
4. **Данные** → `data/`
5. **Изображения** → `assets/`
6. **Скрипты** → `scripts/`
7. **Документация** → `docs/`

## ⚠️ Важные замечания

- Все существующие данные сохранены
- Функциональность бота не изменилась
- API остался прежним
- Только внутренняя структура была реорганизована
