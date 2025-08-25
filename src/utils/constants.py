"""
Constants for Teo bot
Centralized constants to eliminate hardcoded values
"""
import os
from pathlib import Path

# File paths
ASSETS_DIR = Path("assets")
DATA_DIR = Path("data")

# Bot avatar images
BOT_AVATAR_START = ASSETS_DIR / "bot_avatar_for_start.jpeg"
BOT_AVATAR_WEATHER = ASSETS_DIR / "bot_avatar_for_weather.jpg"
BOT_AVATAR_NEWS = ASSETS_DIR / "bot_avatar_for_news.jpeg"
BOT_AVATAR_DEFAULT = ASSETS_DIR / "bot_avatar.jpg"

# Database files
DATABASE_FILE = DATA_DIR / "teo_bot.db"
USER_HABITS_FILE = DATA_DIR / "user_habits.json"

# Default values
DEFAULT_CITY = "Saint Petersburg"
DEFAULT_TIMEZONE = "UTC"
DEFAULT_NOTIFICATION_TIME = "08:00"
DEFAULT_HABIT_TIME = "09:00"
DEFAULT_LANGUAGE = "ru"

# Time formats
TIME_FORMAT = "%H:%M"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Pagination
DEFAULT_PAGE_SIZE = 5
MAX_PAGE_SIZE = 10

# API limits
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10
WEATHER_CACHE_TIME = 300  # 5 minutes
NEWS_CACHE_TIME = 600     # 10 minutes

# Callback data prefixes
CALLBACK_PREFIXES = {
    "WEATHER": "weather_",
    "NEWS": "news_",
    "HABIT": "habit_",
    "FINANCE": "finance_",
    "SETTINGS": "settings_",
    "CITY": "city_",
    "TIME": "time_",
    "TIMEZONE": "timezone_"
}

# Weather conditions
WEATHER_CONDITIONS = {
    "rain": ["rain", "drizzle", "shower"],
    "snow": ["snow", "sleet"],
    "storm": ["thunderstorm"],
    "cloudy": ["clouds", "overcast"],
    "clear": ["clear", "sunny"]
}

# Habit categories
HABIT_CATEGORIES = {
    "health": "Здоровье",
    "productivity": "Продуктивность",
    "learning": "Обучение",
    "fitness": "Фитнес",
    "mindfulness": "Осознанность",
    "social": "Социальное",
    "finance": "Финансы",
    "custom": "Своя"
}

# News categories
NEWS_CATEGORIES = {
    "latest": "Последние новости",
    "popular": "Главные новости",
    "sports": "Спорт",
    "economy": "Экономика и бизнес",
    "technology": "Технологии и наука"
}

# Finance periods
FINANCE_PERIODS = {
    "day": "день",
    "week": "неделю",
    "month": "месяц",
    "year": "год",
    "all": "все время"
}

# Notification types
NOTIFICATION_TYPES = {
    "weather": "Погода",
    "rain": "Дождь",
    "habit": "Привычка",
    "news": "Новости"
}

# Error messages
ERROR_MESSAGES = {
    "file_not_found": "Файл не найден",
    "invalid_input": "Неверный ввод",
    "network_error": "Ошибка сети",
    "api_error": "Ошибка API",
    "database_error": "Ошибка базы данных",
    "permission_error": "Недостаточно прав",
    "timeout_error": "Превышено время ожидания"
}

# Success messages
SUCCESS_MESSAGES = {
    "settings_updated": "Настройки обновлены",
    "habit_created": "Привычка создана",
    "habit_completed": "Привычка выполнена",
    "city_updated": "Город обновлен",
    "time_updated": "Время обновлено",
    "finance_configured": "Финансы настроены"
}

# Emojis
EMOJIS = {
    "weather": "🌤",
    "news": "📰",
    "habit": "🎯",
    "finance": "💰",
    "settings": "⚙️",
    "help": "❓",
    "back": "🔙",
    "refresh": "🔄",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "loading": "⏳",
    "rain": "🌧",
    "sun": "☀️",
    "cloud": "☁️",
    "snow": "❄️",
    "storm": "⛈",
    "city": "🌍",
    "time": "⏰",
    "timezone": "🌐",
    "notification": "🔔",
    "stats": "📊",
    "add": "➕",
    "delete": "🗑️",
    "edit": "✏️",
    "check": "✅",
    "cross": "❌",
    "arrow_right": "➡️",
    "arrow_left": "⬅️",
    "home": "🏠",
    "star": "⭐",
    "fire": "🔥",
    "calendar": "📅",
    "clock": "🕐",
    "chart": "📈",
    "money": "💵",
    "card": "💳",
    "bank": "🏦",
    "shopping": "🛒",
    "food": "🍕",
    "transport": "🚗",
    "entertainment": "🎬",
    "health": "🏥",
    "education": "📚",
    "sport": "⚽",
    "work": "💼",
    "family": "👨‍👩‍👧‍👦",
    "travel": "✈️",
    "gift": "🎁",
    "other": "📦"
}

# Validation rules
VALIDATION_RULES = {
    "city_name": {
        "min_length": 2,
        "max_length": 50,
        "pattern": r"^[a-zA-Zа-яА-Я\s\-']+$"
    },
    "habit_name": {
        "min_length": 3,
        "max_length": 100
    },
    "habit_description": {
        "max_length": 500
    },
    "time_format": {
        "pattern": r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    },
    "url": {
        "pattern": r"^https?://.*$"
    }
}

# Cache keys
CACHE_KEYS = {
    "weather": "weather_{city}",
    "forecast": "forecast_{city}",
    "news": "news_{category}",
    "user_settings": "user_settings_{user_id}",
    "user_habits": "user_habits_{user_id}"
}

# Logging
LOG_LEVELS = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "CRITICAL": "CRITICAL"
}

# Environment variables
ENV_VARS = {
    "BOT_TOKEN": "TELEGRAM_BOT_TOKEN",
    "WEATHER_API_KEY": "WEATHER_API_KEY",
    "NEWS_API_KEY": "NEWS_API_KEY",
    "DEFAULT_CITY": "DEFAULT_CITY",
    "TIMEZONE": "TIMEZONE",
    "LOG_LEVEL": "LOG_LEVEL"
}
