"""
Habit tracking system for Teo bot
Manages user habits, reminders, and completion tracking
"""
import asyncio
import logging
import json
import os
from datetime import datetime, timedelta, time
from typing import Dict, List, Set, Callable, Optional
import threading
import time as time_module

logger = logging.getLogger(__name__)

# Simple file-based storage (in production, use a proper database)
HABITS_FILE = "data/user_habits.json"


class Habit:
    """Represents a user habit"""
    
    def __init__(self, habit_id: str, user_id: int, name: str, description: str = "", 
                 reminder_time: str = "09:00", reminder_days: List[str] = None, 
                 created_date: str = None):
        self.habit_id = habit_id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.reminder_time = reminder_time
        self.reminder_days = reminder_days or ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        self.created_date = created_date or datetime.now().strftime("%Y-%m-%d")
        self.completions = []  # List of completion dates
        self.is_active = True
    
    def to_dict(self) -> Dict:
        """Convert habit to dictionary"""
        return {
            'habit_id': self.habit_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'reminder_time': self.reminder_time,
            'reminder_days': self.reminder_days,
            'created_date': self.created_date,
            'completions': self.completions,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Habit':
        """Create habit from dictionary"""
        habit = cls(
            habit_id=data['habit_id'],
            user_id=data['user_id'],
            name=data['name'],
            description=data.get('description', ''),
            reminder_time=data.get('reminder_time', '09:00'),
            reminder_days=data.get('reminder_days', ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]),
            created_date=data.get('created_date')
        )
        habit.completions = data.get('completions', [])
        habit.is_active = data.get('is_active', True)
        return habit
    
    def mark_completed(self, date: str = None) -> bool:
        """Mark habit as completed for a date"""
        completion_date = date or datetime.now().strftime("%Y-%m-%d")
        
        if completion_date not in self.completions:
            self.completions.append(completion_date)
            return True
        return False
    
    def is_completed_today(self) -> bool:
        """Check if habit is completed today"""
        today = datetime.now().strftime("%Y-%m-%d")
        return today in self.completions
    
    def get_streak(self) -> int:
        """Get current completion streak"""
        if not self.completions:
            return 0
        
        # Sort completions and calculate streak from today backwards
        sorted_completions = sorted(self.completions, reverse=True)
        today = datetime.now()
        streak = 0
        
        for i, completion_date in enumerate(sorted_completions):
            expected_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if completion_date == expected_date:
                streak += 1
            else:
                break
        
        return streak
    
    def get_completion_rate_last_week(self) -> float:
        """Get completion rate for the last 7 days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
        
        expected_days = 0
        completed_days = 0
        
        for i in range(7):
            check_date = start_date + timedelta(days=i)
            day_name = check_date.strftime("%A").lower()
            
            if day_name in self.reminder_days:
                expected_days += 1
                if check_date.strftime("%Y-%m-%d") in self.completions:
                    completed_days += 1
        
        return (completed_days / expected_days * 100) if expected_days > 0 else 0


class HabitTracker:
    """Manages habit tracking system"""
    
    def __init__(self):
        self.habits: Dict[str, Habit] = {}
        self.user_habits: Dict[int, List[str]] = {}  # user_id -> list of habit_ids
        self.reminder_callback: Optional[Callable] = None
        self.monitor_thread = None
        self.running = False
        self.load_habits()
    
    def load_habits(self) -> None:
        """Load habits from file"""
        try:
            if os.path.exists(HABITS_FILE):
                with open(HABITS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for habit_data in data.get('habits', []):
                    habit = Habit.from_dict(habit_data)
                    self.habits[habit.habit_id] = habit
                    
                    # Update user habits index
                    if habit.user_id not in self.user_habits:
                        self.user_habits[habit.user_id] = []
                    if habit.habit_id not in self.user_habits[habit.user_id]:
                        self.user_habits[habit.user_id].append(habit.habit_id)
                
                logger.info(f"Loaded {len(self.habits)} habits from file")
        except Exception as e:
            logger.error(f"Error loading habits: {e}")
            self.habits = {}
            self.user_habits = {}
    
    def save_habits(self) -> None:
        """Save habits to file"""
        try:
            data = {
                'habits': [habit.to_dict() for habit in self.habits.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(HABITS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved {len(self.habits)} habits to file")
        except Exception as e:
            logger.error(f"Error saving habits: {e}")
    
    def create_habit(self, user_id: int, name: str, description: str = "", 
                    reminder_time: str = "09:00", reminder_days: List[str] = None) -> str:
        """Create a new habit"""
        import uuid
        habit_id = str(uuid.uuid4())[:8]  # Short ID
        
        habit = Habit(
            habit_id=habit_id,
            user_id=user_id,
            name=name,
            description=description,
            reminder_time=reminder_time,
            reminder_days=reminder_days
        )
        
        self.habits[habit_id] = habit
        
        # Update user habits index
        if user_id not in self.user_habits:
            self.user_habits[user_id] = []
        self.user_habits[user_id].append(habit_id)
        
        self.save_habits()
        logger.info(f"Created habit '{name}' for user {user_id}")
        
        return habit_id
    
    def get_user_habits(self, user_id: int, active_only: bool = True) -> List[Habit]:
        """Get all habits for a user"""
        habit_ids = self.user_habits.get(user_id, [])
        habits = []
        
        for habit_id in habit_ids:
            if habit_id in self.habits:
                habit = self.habits[habit_id]
                if not active_only or habit.is_active:
                    habits.append(habit)
        
        return sorted(habits, key=lambda h: h.created_date)
    
    def get_habit(self, habit_id: str) -> Optional[Habit]:
        """Get a specific habit"""
        return self.habits.get(habit_id)
    
    def mark_habit_completed(self, habit_id: str, user_id: int) -> bool:
        """Mark a habit as completed"""
        habit = self.habits.get(habit_id)
        if habit and habit.user_id == user_id:
            if habit.mark_completed():
                self.save_habits()
                logger.info(f"Marked habit '{habit.name}' as completed for user {user_id}")
                return True
        return False
    
    def delete_habit(self, habit_id: str, user_id: int) -> bool:
        """Delete a habit"""
        habit = self.habits.get(habit_id)
        if habit and habit.user_id == user_id:
            habit.is_active = False
            self.save_habits()
            logger.info(f"Deleted habit '{habit.name}' for user {user_id}")
            return True
        return False
    
    def update_habit(self, habit_id: str, user_id: int, **kwargs) -> bool:
        """Update habit properties"""
        habit = self.habits.get(habit_id)
        if habit and habit.user_id == user_id:
            for key, value in kwargs.items():
                if hasattr(habit, key):
                    setattr(habit, key, value)
            self.save_habits()
            logger.info(f"Updated habit '{habit.name}' for user {user_id}")
            return True
        return False
    
    def get_habits_for_reminder(self) -> List[Habit]:
        """Get habits that need reminders right now"""
        current_time = datetime.now()
        current_day = current_time.strftime("%A").lower()
        current_hour_min = current_time.strftime("%H:%M")
        
        habits_to_remind = []
        
        for habit in self.habits.values():
            if (habit.is_active and 
                current_day in habit.reminder_days and 
                habit.reminder_time == current_hour_min and
                not habit.is_completed_today()):
                habits_to_remind.append(habit)
        
        return habits_to_remind
    
    def set_reminder_callback(self, callback: Callable) -> None:
        """Set the callback function for sending reminders"""
        self.reminder_callback = callback
        self.start_monitoring()
    
    def start_monitoring(self) -> None:
        """Start the habit reminder monitoring thread"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()
        logger.info("Habit reminder monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the habit reminder monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Habit reminder monitoring stopped")
    
    def _run_monitor(self) -> None:
        """Run the habit reminder monitoring loop"""
        while self.running:
            try:
                habits_to_remind = self.get_habits_for_reminder()
                
                for habit in habits_to_remind:
                    if self.reminder_callback:
                        asyncio.create_task(self.reminder_callback(habit))
                
            except Exception as e:
                logger.error(f"Error in habit monitoring loop: {e}")
            
            # Check every minute
            time_module.sleep(60)
    
    def format_habit_list(self, habits: List[Habit]) -> str:
        """Format a list of habits for display"""
        if not habits:
            return "У тебя пока нет активных привычек."
        
        message = "📋 **Твои привычки:**\n\n"
        
        for habit in habits:
            status = "✅" if habit.is_completed_today() else "⏳"
            streak = habit.get_streak()
            streak_text = f" • Серия: {streak} дн." if streak > 0 else ""
            
            message += f"{status} **{habit.name}**{streak_text}\n"
            if habit.description:
                message += f"   _{habit.description}_\n"
            message += f"   ⏰ {habit.reminder_time} • Дни: {len(habit.reminder_days)}/7\n\n"
        
        return message
    
    def get_stats_message(self, user_id: int) -> str:
        """Get statistics message for user"""
        habits = self.get_user_habits(user_id)
        
        if not habits:
            return "📊 **Статистика привычек**\n\nУ тебя пока нет привычек для отслеживания."
        
        total_habits = len(habits)
        completed_today = sum(1 for h in habits if h.is_completed_today())
        total_streak = sum(h.get_streak() for h in habits)
        avg_completion = sum(h.get_completion_rate_last_week() for h in habits) / total_habits
        
        message = f"""📊 **Статистика привычек**

📈 **Сегодня:** {completed_today}/{total_habits} выполнено
🔥 **Общая серия:** {total_streak} дней
📅 **За неделю:** {avg_completion:.1f}% выполнение
🎯 **Всего привычек:** {total_habits}

"""
        
        # Show top performing habits
        if habits:
            best_habit = max(habits, key=lambda h: h.get_streak())
            if best_habit.get_streak() > 0:
                message += f"🏆 **Лучшая серия:** {best_habit.name} ({best_habit.get_streak()} дн.)"
        
        return message
