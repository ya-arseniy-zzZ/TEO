"""
Rain monitoring system for Teo bot
Monitors weather for rain alerts and sends umbrella reminders
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Callable, Optional
import threading
import time

from src.services.weather_service import WeatherService
from src.utils.config import DEFAULT_CITY

logger = logging.getLogger(__name__)


class RainMonitor:
    """Monitors weather for rain alerts"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.monitored_users: Dict[int, Dict] = {}
        self.rain_callback: Optional[Callable] = None
        self.monitor_thread = None
        self.running = False
        self.last_check_time = {}
        
    def set_rain_callback(self, callback: Callable) -> None:
        """Set the callback function for sending rain alerts"""
        self.rain_callback = callback
        self.start_monitoring()
    
    def add_user(self, user_id: int, user_settings: Dict) -> None:
        """Add a user to rain monitoring"""
        if not user_settings.get('rain_alerts_enabled', True):  # Default enabled
            return
        
        self.monitored_users[user_id] = {
            'city': user_settings.get('city', DEFAULT_CITY),
            'settings': user_settings,
            'last_rain_alert': None
        }
        
        logger.info(f"Added user {user_id} to rain monitoring for {self.monitored_users[user_id]['city']}")
    
    def remove_user(self, user_id: int) -> None:
        """Remove a user from rain monitoring"""
        if user_id in self.monitored_users:
            del self.monitored_users[user_id]
            logger.info(f"Removed user {user_id} from rain monitoring")
    
    def update_user_city(self, user_id: int, new_city: str) -> None:
        """Update user's city for rain monitoring"""
        if user_id in self.monitored_users:
            self.monitored_users[user_id]['city'] = new_city
            logger.info(f"Updated rain monitoring city for user {user_id} to {new_city}")
    
    def enable_rain_alerts(self, user_id: int, user_settings: Dict) -> None:
        """Enable rain alerts for a user"""
        user_settings['rain_alerts_enabled'] = True
        self.add_user(user_id, user_settings)
    
    def disable_rain_alerts(self, user_id: int) -> None:
        """Disable rain alerts for a user"""
        self.remove_user(user_id)
    
    def check_rain_for_user(self, user_id: int) -> Optional[Dict]:
        """Check if rain is expected for a specific user"""
        if user_id not in self.monitored_users:
            return None
        
        user_data = self.monitored_users[user_id]
        city = user_data['city']
        
        # Get hourly forecast
        hourly_forecast = self.weather_service.get_hourly_forecast(city, hours=4)
        if not hourly_forecast:
            return None
        
        # Check for rain in the next 1-2 hours
        rain_info = self.weather_service.is_rain_expected(hourly_forecast, hours_ahead=2)
        
        return rain_info if rain_info['rain_expected'] else None
    
    def should_send_rain_alert(self, user_id: int, rain_info: Dict) -> bool:
        """Determine if we should send a rain alert to user"""
        if not rain_info or not rain_info['rain_expected']:
            return False
        
        user_data = self.monitored_users.get(user_id)
        if not user_data:
            return False
        
        # Don't send multiple alerts for the same rain event
        last_alert = user_data.get('last_rain_alert')
        if last_alert:
            # If we sent an alert in the last 3 hours, don't send another
            time_since_last = datetime.now() - last_alert
            if time_since_last < timedelta(hours=3):
                return False
        
        return True
    
    def format_rain_alert_message(self, city: str, rain_info: Dict) -> str:
        """Format a rain alert message"""
        time_str = rain_info['time'].split(' ')[1]  # Extract time from datetime
        
        message = f"""☔ **Предупреждение о дожде!**

🌧 {rain_info['message']} в **{city}**
⏰ Примерное время: **{time_str}**

🌂 **Не забудь взять зонт!**

Это автоматическое уведомление поможет тебе подготовиться к непогоде."""
        
        return message
    
    async def send_rain_alert(self, user_id: int, rain_info: Dict) -> None:
        """Send rain alert to a user"""
        if not self.rain_callback:
            logger.error("No rain callback set")
            return
        
        user_data = self.monitored_users.get(user_id)
        if not user_data:
            return
        
        city = user_data['city']
        message = self.format_rain_alert_message(city, rain_info)
        
        try:
            # Run the callback in an async context
            await self.rain_callback(user_id, message)
            
            # Update last alert time
            user_data['last_rain_alert'] = datetime.now()
            
            logger.info(f"Rain alert sent to user {user_id} for {city}")
            
        except Exception as e:
            logger.error(f"Error sending rain alert to user {user_id}: {e}")
    
    def check_all_users_for_rain(self) -> None:
        """Check all monitored users for rain and send alerts"""
        if not self.rain_callback:
            return
        
        for user_id in list(self.monitored_users.keys()):
            try:
                rain_info = self.check_rain_for_user(user_id)
                
                if rain_info and self.should_send_rain_alert(user_id, rain_info):
                    # Schedule the alert to be sent
                    asyncio.create_task(self.send_rain_alert(user_id, rain_info))
                    
            except Exception as e:
                logger.error(f"Error checking rain for user {user_id}: {e}")
    
    def start_monitoring(self) -> None:
        """Start the rain monitoring thread"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()
        logger.info("Rain monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the rain monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Rain monitoring stopped")
    
    def _run_monitor(self) -> None:
        """Run the rain monitoring loop"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check every 30 minutes
                for user_id in list(self.monitored_users.keys()):
                    last_check = self.last_check_time.get(user_id, datetime.min)
                    time_since_check = current_time - last_check
                    
                    if time_since_check >= timedelta(minutes=30):
                        self.last_check_time[user_id] = current_time
                        
                        # Check this user for rain
                        rain_info = self.check_rain_for_user(user_id)
                        if rain_info and self.should_send_rain_alert(user_id, rain_info):
                            asyncio.create_task(self.send_rain_alert(user_id, rain_info))
                
            except Exception as e:
                logger.error(f"Error in rain monitoring loop: {e}")
            
            # Wait 5 minutes before next iteration
            time.sleep(300)
    
    def get_monitored_users(self) -> Dict[int, str]:
        """Get a list of all monitored users and their cities"""
        return {
            user_id: data['city'] 
            for user_id, data in self.monitored_users.items()
        }
    
    def is_user_monitored(self, user_id: int) -> bool:
        """Check if a user is being monitored for rain"""
        return user_id in self.monitored_users
