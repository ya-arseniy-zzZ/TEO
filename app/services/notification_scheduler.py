"""
Notification scheduler for Teo bot
Handles scheduling and sending of daily weather notifications
"""
import asyncio
import logging
from datetime import datetime, time
from typing import Dict, Callable, Optional
import pytz
import schedule
import threading

from app.utils.config import TIMEZONE

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Handles scheduling of weather notifications"""
    
    def __init__(self):
        self.user_schedules: Dict[int, Dict] = {}
        self.notification_callback: Optional[Callable] = None
        self.scheduler_thread = None
        self.running = False
        self._stop_event = threading.Event()
    
    def set_notification_callback(self, callback: Callable) -> None:
        """Set the callback function for sending notifications"""
        self.notification_callback = callback
        self.start_scheduler()
    
    def add_user(self, user_id: int, user_settings: Dict) -> None:
        """Add a user to the notification schedule"""
        if not user_settings.get('notifications_enabled', False):
            return
        
        notification_time = user_settings.get('notification_time', '08:00')
        user_timezone = user_settings.get('timezone', TIMEZONE)
        
        # Remove existing schedule for this user
        self.remove_user(user_id)
        
        # Add new schedule
        self.user_schedules[user_id] = {
            'time': notification_time,
            'timezone': user_timezone,
            'settings': user_settings
        }
        
        # Schedule the notification
        schedule.every().day.at(notification_time).do(
            self._send_notification_wrapper, user_id
        ).tag(f'user_{user_id}')
        
        logger.info(f"Added notification schedule for user {user_id} at {notification_time} ({user_timezone})")
    
    def remove_user(self, user_id: int) -> None:
        """Remove a user from the notification schedule"""
        if user_id in self.user_schedules:
            # Cancel existing scheduled jobs for this user
            schedule.clear(f'user_{user_id}')
            del self.user_schedules[user_id]
            logger.info(f"Removed notification schedule for user {user_id}")
    
    def update_user_time(self, user_id: int, new_time: str) -> None:
        """Update notification time for a user"""
        if user_id in self.user_schedules:
            self.user_schedules[user_id]['time'] = new_time
            self.user_schedules[user_id]['settings']['notification_time'] = new_time
            
            # Re-add the user with new time
            self.add_user(user_id, self.user_schedules[user_id]['settings'])
    
    def _send_notification_wrapper(self, user_id: int) -> None:
        """Wrapper for sending notifications that handles timezone conversion"""
        if not self.notification_callback:
            logger.error("No notification callback set")
            return
        
        user_data = self.user_schedules.get(user_id)
        if not user_data:
            logger.error(f"No schedule data found for user {user_id}")
            return
        
        # Check if it's the right time for this user's timezone
        user_tz = pytz.timezone(user_data['timezone'])
        current_time = datetime.now(user_tz).time()
        scheduled_time = datetime.strptime(user_data['time'], '%H:%M').time()
        
        # Allow a 1-minute window for execution
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute) - 
            (scheduled_time.hour * 60 + scheduled_time.minute)
        )
        
        if time_diff <= 1:  # Within 1 minute
            # Run the notification callback in an async context
            asyncio.create_task(self.notification_callback(user_id))
            logger.info(f"Triggered notification for user {user_id}")
        else:
            logger.debug(f"Skipping notification for user {user_id} - time mismatch")
    
    def start_scheduler(self) -> None:
        """Start the scheduler thread"""
        if self.running:
            return
        
        # Clear any existing schedules
        schedule.clear()
        
        self.running = True
        self._stop_event.clear()
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Notification scheduler started")
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler"""
        self.running = False
        self._stop_event.set()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Notification scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler in a separate thread"""
        while self.running:
            try:
                schedule.run_pending()
                # Check every minute
                self._stop_event.wait(60)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait a bit before retrying
                self._stop_event.wait(10)
    
    def get_user_schedule(self, user_id: int) -> Optional[Dict]:
        """Get schedule information for a user"""
        return self.user_schedules.get(user_id)
    
    def list_scheduled_users(self) -> Dict[int, str]:
        """Get a list of all users with active schedules"""
        return {
            user_id: data['time'] 
            for user_id, data in self.user_schedules.items()
        }
    
    def debug_scheduler_status(self) -> str:
        """Get debug information about scheduler status"""
        scheduled_users = self.list_scheduled_users()
        jobs = schedule.get_jobs()
        
        debug_info = f"""
Scheduler Status:
- Running: {self.running}
- Total scheduled users: {len(scheduled_users)}
- Total jobs: {len(jobs)}
- Scheduled users: {scheduled_users}
- Jobs: {[f'{job.job_func.__name__} at {job.at_time}' for job in jobs]}
"""
        return debug_info


