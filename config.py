"""
Configuration settings for Teo personal assistant bot
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
DEFAULT_CITY = os.getenv('DEFAULT_CITY', 'London')
TIMEZONE = os.getenv('TIMEZONE', 'UTC')

# Weather API settings
WEATHER_API_BASE_URL = "http://api.openweathermap.org/data/2.5"

# Bot settings
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is required. Please set it in your .env file.")

if not WEATHER_API_KEY:
    raise ValueError("WEATHER_API_KEY is required. Please get one from openweathermap.org and set it in your .env file.")
