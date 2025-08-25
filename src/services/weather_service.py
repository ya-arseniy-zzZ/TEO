"""
Weather service for fetching weather data from OpenWeatherMap API
"""
import requests
import logging
from typing import Dict, Optional
from src.utils.config import WEATHER_API_KEY, WEATHER_API_BASE_URL, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching weather information"""
    
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = WEATHER_API_BASE_URL
    
    def get_current_weather(self, city: str) -> Optional[Dict]:
        """
        Get current weather for a city
        
        Args:
            city: City name
            
        Returns:
            Dictionary with weather information or None if error
        """
        try:
            url = f"{self.base_url}/weather"
            params = {
                'q': city,
                'appid': self.api_key,
                'units': 'metric'  # Use Celsius
            }
            
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            # Format the weather data
            weather_info = {
                'city': data['name'],
                'country': data['sys']['country'],
                'temperature': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind'].get('speed', 0)
            }
            
            return weather_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {e}")
            return None
        except KeyError as e:
            logger.error(f"Error parsing weather data: {e}")
            return None
    
    def get_weather_forecast(self, city: str, days: int = 3) -> Optional[Dict]:
        """
        Get weather forecast for a city
        
        Args:
            city: City name
            days: Number of days to forecast (max 5)
            
        Returns:
            Dictionary with forecast information or None if error
        """
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'q': city,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': min(days * 8, 40)  # 8 forecasts per day (every 3 hours), max 40
            }
            
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            # Format forecast data
            forecasts = []
            for item in data['list'][:days * 8:8]:  # Take one forecast per day
                forecast = {
                    'date': item['dt_txt'].split(' ')[0],
                    'temperature': round(item['main']['temp']),
                    'description': item['weather'][0]['description'].title(),
                    'humidity': item['main']['humidity'],
                    'wind_speed': item['wind'].get('speed', 0)
                }
                forecasts.append(forecast)
            
            return {
                'city': data['city']['name'],
                'country': data['city']['country'],
                'forecasts': forecasts
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching forecast data: {e}")
            return None
        except KeyError as e:
            logger.error(f"Error parsing forecast data: {e}")
            return None
    
    def format_weather_message(self, weather_data: Dict) -> str:
        """
        Format weather data into a readable message
        
        Args:
            weather_data: Weather data dictionary
            
        Returns:
            Formatted weather message
        """
        if not weather_data:
            return "❌ Извини, не удалось получить данные о погоде."
        
        message = f"""🌤 <b>Погода в {weather_data['city']}, {weather_data['country']}</b>

<blockquote>🌡 Температура: {weather_data['temperature']}°C (ощущается как {weather_data['feels_like']}°C)
☁️ Состояние: {weather_data['description']}
💧 Влажность: {weather_data['humidity']}%
💨 Скорость ветра: {weather_data['wind_speed']} м/с</blockquote>"""
        
        return message
    
    def format_forecast_message(self, forecast_data: Dict) -> str:
        """
        Format forecast data into a readable message
        
        Args:
            forecast_data: Forecast data dictionary
            
        Returns:
            Formatted forecast message
        """
        if not forecast_data:
            return "❌ Извини, не удалось получить данные прогноза."
        
        message = f"📅 <b>Прогноз на 3 дня для {forecast_data['city']}, {forecast_data['country']}</b>\n\n"
        
        for forecast in forecast_data['forecasts']:
            message += f"<b>{forecast['date']}</b>\n"
            message += f"<blockquote>🌡 {forecast['temperature']}°C | {forecast['description']}\n"
            message += f"💧 {forecast['humidity']}% | 💨 {forecast['wind_speed']} м/с</blockquote>\n\n"
        
        return message
    
    def get_hourly_forecast(self, city: str, hours: int = 12) -> Optional[Dict]:
        """
        Get hourly weather forecast for rain detection
        
        Args:
            city: City name
            hours: Number of hours to forecast (max 48)
            
        Returns:
            Dictionary with hourly forecast information or None if error
        """
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'q': city,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': min(hours, 40)  # Max 40 entries (5 days * 8 per day)
            }
            
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            # Format hourly forecast data
            hourly_forecasts = []
            for item in data['list'][:hours]:
                forecast = {
                    'datetime': item['dt_txt'],
                    'timestamp': item['dt'],
                    'temperature': round(item['main']['temp']),
                    'description': item['weather'][0]['description'].lower(),
                    'weather_id': item['weather'][0]['id'],
                    'rain_probability': item.get('pop', 0) * 100,  # Probability of precipitation
                    'rain_volume': item.get('rain', {}).get('3h', 0)  # Rain volume in mm
                }
                hourly_forecasts.append(forecast)
            
            return {
                'city': data['city']['name'],
                'country': data['city']['country'],
                'forecasts': hourly_forecasts
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching hourly forecast data: {e}")
            return None
        except KeyError as e:
            logger.error(f"Error parsing hourly forecast data: {e}")
            return None
    
    def get_next_3_hours_forecast(self, city: str) -> Optional[Dict]:
        """
        Get weather forecast for the next 3 full hours (e.g., if it's 11:19, get 12:00, 13:00, 14:00)
        
        Args:
            city: City name
            
        Returns:
            Dictionary with next 3 hours forecast information or None if error
        """
        try:
            from datetime import datetime, timedelta
            
            # Get current time
            now = datetime.now()
            current_hour = now.hour
            
            # Calculate next 3 full hours
            next_hours = []
            for i in range(1, 4):  # Next 1, 2, 3 hours
                next_hour = current_hour + i
                if next_hour >= 24:
                    next_hour -= 24
                next_hours.append(next_hour)
            
            # Get hourly forecast data
            hourly_forecast = self.get_hourly_forecast(city, hours=12)  # Get more data to find the right hours
            if not hourly_forecast or 'forecasts' not in hourly_forecast:
                return None
            
            # Create synthetic forecasts for the next 3 consecutive hours
            next_3_hours_forecasts = []
            
            for target_hour in next_hours:
                # Find the closest available forecast for this hour
                closest_forecast = None
                min_hour_diff = 24
                
                for forecast in hourly_forecast['forecasts']:
                    forecast_time = datetime.fromisoformat(forecast['datetime'].replace('Z', '+00:00'))
                    forecast_hour = forecast_time.hour
                    
                    # Calculate hour difference (considering 24-hour cycle)
                    hour_diff = abs(forecast_hour - target_hour)
                    if hour_diff > 12:  # Handle day boundary
                        hour_diff = 24 - hour_diff
                    
                    if hour_diff < min_hour_diff:
                        min_hour_diff = hour_diff
                        closest_forecast = forecast
                
                if closest_forecast:
                    # Create a synthetic forecast for the target hour
                    synthetic_forecast = closest_forecast.copy()
                    
                    # Update the datetime to reflect the target hour
                    original_time = datetime.fromisoformat(closest_forecast['datetime'].replace('Z', '+00:00'))
                    target_time = original_time.replace(hour=target_hour)
                    synthetic_forecast['datetime'] = target_time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    next_3_hours_forecasts.append(synthetic_forecast)
            
            # Sort by hour to ensure correct order
            next_3_hours_forecasts.sort(key=lambda x: datetime.fromisoformat(x['datetime'].replace('Z', '+00:00')).hour)
            
            return {
                'city': hourly_forecast['city'],
                'country': hourly_forecast['country'],
                'forecasts': next_3_hours_forecasts,
                'next_hours': next_hours
            }
            
        except Exception as e:
            logger.error(f"Error getting next 3 hours forecast: {e}")
            return None
    
    def is_rain_expected(self, hourly_forecast: Dict, hours_ahead: int = 1) -> Dict:
        """
        Check if rain is expected within specified hours
        
        Args:
            hourly_forecast: Hourly forecast data
            hours_ahead: How many hours ahead to check
            
        Returns:
            Dictionary with rain prediction info
        """
        if not hourly_forecast or 'forecasts' not in hourly_forecast:
            return {'rain_expected': False, 'message': ''}
        
        rain_conditions = []
        
        # Check forecasts within the specified timeframe
        for forecast in hourly_forecast['forecasts'][:hours_ahead]:
            weather_id = forecast['weather_id']
            rain_prob = forecast['rain_probability']
            description = forecast['description']
            
            # Weather condition IDs for rain/drizzle/thunderstorm
            # 2xx: Thunderstorm, 3xx: Drizzle, 5xx: Rain
            is_rain = (200 <= weather_id <= 299 or  # Thunderstorm
                      300 <= weather_id <= 399 or  # Drizzle
                      500 <= weather_id <= 599)    # Rain
            
            # Also check for high probability of precipitation
            high_rain_prob = rain_prob > 50
            
            if is_rain or high_rain_prob:
                rain_conditions.append({
                    'time': forecast['datetime'],
                    'description': description,
                    'probability': rain_prob,
                    'is_certain': is_rain
                })
        
        if rain_conditions:
            # Get the earliest rain condition
            earliest_rain = rain_conditions[0]
            
            intensity = "дождь"
            if any(word in earliest_rain['description'] for word in ['heavy', 'интенсивный']):
                intensity = "сильный дождь"
            elif any(word in earliest_rain['description'] for word in ['light', 'слабый']):
                intensity = "небольшой дождь"
            elif any(word in earliest_rain['description'] for word in ['thunder', 'гроза']):
                intensity = "грозу"
            
            probability_text = ""
            if not earliest_rain['is_certain'] and earliest_rain['probability'] > 0:
                probability_text = f" (вероятность {earliest_rain['probability']:.0f}%)"
            
            return {
                'rain_expected': True,
                'time': earliest_rain['time'],
                'intensity': intensity,
                'probability': earliest_rain['probability'],
                'message': f"Ожидается {intensity}{probability_text}"
            }
        
        return {'rain_expected': False, 'message': ''}
