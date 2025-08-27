"""
SQLite database manager for Teo bot
Handles all database operations for users, weather settings, and habits
"""
import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_PATH = "data/teo_bot.db"


class DatabaseManager:
    """Manages SQLite database operations for Teo bot"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Get thread-safe database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
        
        try:
            yield self._local.connection
        except Exception as e:
            self._local.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        else:
            self._local.connection.commit()
    
    def init_database(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table - basic user information without personal data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language_code TEXT DEFAULT 'ru',
                    is_active BOOLEAN DEFAULT 1,
                    google_sheets_url TEXT,
                    finance_sheet_name TEXT DEFAULT 'Sheet1',
                    main_message_id INTEGER,
                    current_state TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add finance_sheet_name column if it doesn't exist
            self.add_column_if_not_exists('users', 'finance_sheet_name', 'TEXT DEFAULT "Sheet1"')
            self.add_column_if_not_exists('users', 'google_sheets_url', 'TEXT')
            self.add_column_if_not_exists('users', 'main_message_id', 'INTEGER')
            self.add_column_if_not_exists('users', 'current_state', 'TEXT')
            self.add_column_if_not_exists('users', 'data_count', 'INTEGER DEFAULT 0')
            
            # User budgets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    budget_limit REAL NOT NULL,
                    current_spent REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            """)
            
            # Finance auto refresh settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS finance_auto_refresh (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT 0,
                    frequency TEXT DEFAULT 'daily',
                    last_refresh TIMESTAMP,
                    next_refresh TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            """)
            
            # Category mapping rules
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS category_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    original_category TEXT NOT NULL,
                    mapped_category TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            """)
            
            # Weather settings table - linked to users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    city TEXT DEFAULT 'Saint Petersburg',
                    timezone TEXT DEFAULT 'UTC',
                    daily_notifications_enabled BOOLEAN DEFAULT 0,
                    notification_time TEXT DEFAULT '08:00',
                    rain_alerts_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            """)
            
            # Habits table - linked to users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    reminder_time TEXT DEFAULT '09:00',
                    reminder_days TEXT DEFAULT '["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]',
                    timezone TEXT DEFAULT 'Europe/Moscow',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            """)
            
            # Habit completions table - tracks daily completions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id TEXT NOT NULL,
                    user_id INTEGER,
                    completion_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(habit_id, completion_date),
                    FOREIGN KEY (habit_id) REFERENCES habits (habit_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_user_id ON weather_settings(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_habits_user_id ON habits(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_habits_active ON habits(user_id, is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_completions_habit ON habit_completions(habit_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_completions_date ON habit_completions(completion_date)")
            
            logger.info("Database initialized successfully")
    
    # User operations
    def create_or_update_user(self, user_id: int, username: str = None, 
                             first_name: str = None, language_code: str = 'ru') -> bool:
        """Create or update user record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, language_code, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = COALESCE(excluded.username, username),
                        first_name = COALESCE(excluded.first_name, first_name),
                        language_code = COALESCE(excluded.language_code, language_code),
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, username, first_name, language_code))
                
                # Create default weather settings if user is new
                cursor.execute("""
                    INSERT OR IGNORE INTO weather_settings (user_id)
                    VALUES (?)
                """, (user_id,))
                
                return True
        except Exception as e:
            logger.error(f"Error creating/updating user {user_id}: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user (soft delete)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False
    
    # Weather settings operations
    def get_weather_settings(self, user_id: int) -> Optional[Dict]:
        """Get weather settings for user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM weather_settings WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting weather settings for user {user_id}: {e}")
            return None
    
    def update_weather_settings(self, user_id: int, **kwargs) -> bool:
        """Update weather settings for user"""
        try:
            if not kwargs:
                return True
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            allowed_fields = [
                'city', 'timezone', 'daily_notifications_enabled', 
                'notification_time', 'rain_alerts_enabled'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = ?")
                    values.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            query = f"""
                UPDATE weather_settings 
                SET {', '.join(set_clauses)}
                WHERE user_id = ?
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating weather settings for user {user_id}: {e}")
            return False
    
    def get_users_with_daily_notifications(self) -> List[Dict]:
        """Get all users with daily notifications enabled"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.user_id, u.first_name, ws.*
                    FROM users u
                    JOIN weather_settings ws ON u.user_id = ws.user_id
                    WHERE u.is_active = 1 AND ws.daily_notifications_enabled = 1
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting users with daily notifications: {e}")
            return []
    
    def get_users_with_rain_alerts(self) -> List[Dict]:
        """Get all users with rain alerts enabled"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.user_id, u.first_name, ws.*
                    FROM users u
                    JOIN weather_settings ws ON u.user_id = ws.user_id
                    WHERE u.is_active = 1 AND ws.rain_alerts_enabled = 1
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting users with rain alerts: {e}")
            return []
    
    # Habit operations
    def create_habit(self, habit_id: str, user_id: int, name: str, 
                    description: str = '', reminder_time: str = '09:00',
                    reminder_days: List[str] = None, timezone: str = 'Europe/Moscow') -> bool:
        """Create a new habit"""
        try:
            if reminder_days is None:
                reminder_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            
            reminder_days_json = json.dumps(reminder_days)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO habits (habit_id, user_id, name, description, reminder_time, reminder_days, timezone)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (habit_id, user_id, name, description, reminder_time, reminder_days_json, timezone))
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error creating habit {habit_id}: {e}")
            return False
    
    def get_user_habits(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """Get all habits for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM habits WHERE user_id = ?"
                params = [user_id]
                
                if active_only:
                    query += " AND is_active = 1"
                
                query += " ORDER BY created_at"
                
                cursor.execute(query, params)
                habits = []
                
                for row in cursor.fetchall():
                    habit = dict(row)
                    # Parse JSON reminder_days
                    habit['reminder_days'] = json.loads(habit['reminder_days'])
                    habits.append(habit)
                
                return habits
        except Exception as e:
            logger.error(f"Error getting habits for user {user_id}: {e}")
            return []
    
    def get_habit(self, habit_id: str) -> Optional[Dict]:
        """Get a specific habit"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM habits WHERE habit_id = ?", (habit_id,))
                row = cursor.fetchone()
                
                if row:
                    habit = dict(row)
                    habit['reminder_days'] = json.loads(habit['reminder_days'])
                    return habit
                return None
        except Exception as e:
            logger.error(f"Error getting habit {habit_id}: {e}")
            return None
    
    def update_habit(self, habit_id: str, **kwargs) -> bool:
        """Update habit properties"""
        try:
            if not kwargs:
                return True
            
            # Handle reminder_days JSON serialization
            if 'reminder_days' in kwargs:
                kwargs['reminder_days'] = json.dumps(kwargs['reminder_days'])
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            allowed_fields = ['name', 'description', 'reminder_time', 'reminder_days', 'timezone', 'is_active']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = ?")
                    values.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(habit_id)
            
            query = f"""
                UPDATE habits 
                SET {', '.join(set_clauses)}
                WHERE habit_id = ?
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating habit {habit_id}: {e}")
            return False
    
    def delete_habit(self, habit_id: str) -> bool:
        """Delete habit (soft delete)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE habits SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE habit_id = ?
                """, (habit_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting habit {habit_id}: {e}")
            return False
    
    # Habit completion operations
    def mark_habit_completed(self, habit_id: str, user_id: int, 
                           completion_date: str = None) -> bool:
        """Mark habit as completed for a date"""
        try:
            if completion_date is None:
                completion_date = datetime.now().strftime("%Y-%m-%d")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO habit_completions (habit_id, user_id, completion_date)
                    VALUES (?, ?, ?)
                """, (habit_id, user_id, completion_date))
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking habit {habit_id} completed: {e}")
            return False
    
    def is_habit_completed_today(self, habit_id: str) -> bool:
        """Check if habit is completed today"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM habit_completions 
                    WHERE habit_id = ? AND completion_date = ?
                """, (habit_id, today))
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking completion for habit {habit_id}: {e}")
            return False
    
    def get_habit_completions(self, habit_id: str, days: int = 30) -> List[str]:
        """Get habit completions for the last N days"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT completion_date 
                    FROM habit_completions 
                    WHERE habit_id = ? 
                    AND completion_date >= date('now', '-{} days')
                    ORDER BY completion_date DESC
                """.format(days), (habit_id,))
                
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting completions for habit {habit_id}: {e}")
            return []
    
    def get_habits_for_reminder(self, current_time: str, current_day: str) -> List[Dict]:
        """Get habits that need reminders right now"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT h.*, u.first_name
                    FROM habits h
                    JOIN users u ON h.user_id = u.user_id
                    LEFT JOIN habit_completions hc ON h.habit_id = hc.habit_id 
                        AND hc.completion_date = date('now')
                    WHERE h.is_active = 1 
                        AND u.is_active = 1
                        AND h.reminder_time = ?
                        AND h.reminder_days LIKE ?
                        AND hc.id IS NULL
                """, (current_time, f'%{current_day}%'))
                
                habits = []
                for row in cursor.fetchall():
                    habit = dict(row)
                    habit['reminder_days'] = json.loads(habit['reminder_days'])
                    # Double-check day is actually in the list (LIKE can be imprecise)
                    if current_day in habit['reminder_days']:
                        habits.append(habit)
                
                return habits
        except Exception as e:
            logger.error(f"Error getting habits for reminder: {e}")
            return []
    
    # Database maintenance
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                stats['active_users'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM habits WHERE is_active = 1")
                stats['active_habits'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM habit_completions WHERE completion_date = date('now')")
                stats['completions_today'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM weather_settings WHERE daily_notifications_enabled = 1")
                stats['weather_subscribers'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM weather_settings WHERE rain_alerts_enabled = 1")
                stats['rain_alert_subscribers'] = cursor.fetchone()[0]
                
                return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 90) -> bool:
        """Clean up old completion data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM habit_completions 
                    WHERE completion_date < date('now', '-{} days')
                """.format(days))
                
                deleted_rows = cursor.rowcount
                logger.info(f"Cleaned up {deleted_rows} old completion records")
                return True
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False
    
    # Finance settings operations
    def get_finance_settings(self, user_id: int) -> Optional[Dict[str, str]]:
        """Get Google Sheets URL and sheet name for user's finance tracking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT google_sheets_url, finance_sheet_name FROM users WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    return {
                        'url': row[0],
                        'sheet_name': row[1] if row[1] else 'Sheet1'
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting finance settings for user {user_id}: {e}")
            return None
    
    def update_finance_settings(self, user_id: int, google_sheets_url: str = None, sheet_name: str = 'Sheet1') -> bool:
        """Update Google Sheets URL and sheet name for user's finance tracking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET google_sheets_url = ?, finance_sheet_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (google_sheets_url, sheet_name, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating finance settings for user {user_id}: {e}")
            return False
    
    def add_column_if_not_exists(self, table: str, column: str, column_type: str) -> bool:
        """Add a column to a table if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if column exists
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                
                if column not in columns:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                    logger.info(f"Added column {column} to table {table}")
                    return True
                else:
                    logger.info(f"Column {column} already exists in table {table}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error adding column {column} to table {table}: {e}")
            return False
    
    # Single Message Interface methods
    def save_user_main_message(self, user_id: int, message_id: int) -> bool:
        """Save user's main message ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users (user_id, main_message_id, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, message_id))
                return True
        except Exception as e:
            logger.error(f"Error saving main message for user {user_id}: {e}")
            return False
    
    def get_user_main_message_id(self, user_id: int) -> Optional[int]:
        """Get user's main message ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT main_message_id FROM users WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                return row[0] if row and row[0] else None
        except Exception as e:
            logger.error(f"Error getting main message for user {user_id}: {e}")
            return None
    
    def set_user_state(self, user_id: int, state: str) -> bool:
        """Set user's current state"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users (user_id, current_state, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, state))
                return True
        except Exception as e:
            logger.error(f"Error setting state for user {user_id}: {e}")
            return False
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        """Get user's current state"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT current_state FROM users WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                return row[0] if row and row[0] else None
        except Exception as e:
            logger.error(f"Error getting state for user {user_id}: {e}")
            return None
    
    def clear_user_state(self, user_id: int) -> bool:
        """Clear user's current state"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET current_state = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                return True
        except Exception as e:
            logger.error(f"Error clearing state for user {user_id}: {e}")
            return False
    
    # Anchor-UX methods
    def save_anchor_session(self, user_id: int, chat_id: int, session_data: Dict[str, Any]) -> bool:
        """Save Anchor-UX session data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create anchor_sessions table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS anchor_sessions (
                        user_id INTEGER,
                        chat_id INTEGER,
                        session_data TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, chat_id)
                    )
                """)
                
                import json
                session_json = json.dumps(session_data, ensure_ascii=False)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO anchor_sessions (user_id, chat_id, session_data, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, chat_id, session_json))
                
                return True
        except Exception as e:
            logger.error(f"Error saving anchor session for user {user_id}: {e}")
            return False
    
    def get_anchor_session(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get Anchor-UX session data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create anchor_sessions table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS anchor_sessions (
                        user_id INTEGER,
                        chat_id INTEGER,
                        session_data TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, chat_id)
                    )
                """)
                
                cursor.execute("""
                    SELECT session_data FROM anchor_sessions WHERE user_id = ? AND chat_id = ?
                """, (user_id, chat_id))
                
                row = cursor.fetchone()
                if row and row[0]:
                    import json
                    return json.loads(row[0])
                return None
        except Exception as e:
            logger.error(f"Error getting anchor session for user {user_id}: {e}")
            return None
    
    def clear_anchor_session(self, user_id: int, chat_id: int) -> bool:
        """Clear Anchor-UX session data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM anchor_sessions WHERE user_id = ? AND chat_id = ?
                """, (user_id, chat_id))
                return True
        except Exception as e:
            logger.error(f"Error clearing anchor session for user {user_id}: {e}")
            return False
    
    def cleanup_expired_anchor_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired anchor sessions"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM anchor_sessions 
                    WHERE updated_at < datetime('now', '-{} hours')
                """.format(max_age_hours))
                
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} expired anchor sessions")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up expired anchor sessions: {e}")
            return 0
    
    def get_user_budgets(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's budgets with current spending"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT category, budget_limit, current_spent, created_at, updated_at
                    FROM user_budgets 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                """, (user_id,))
                
                budgets = []
                for row in cursor.fetchall():
                    budgets.append({
                        'category': row[0],
                        'limit': row[1],
                        'spent': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    })
                
                return budgets
        except Exception as e:
            logger.error(f"Error getting budgets for user {user_id}: {e}")
            return []
    
    def add_user_budget(self, user_id: int, category: str, budget_limit: float) -> bool:
        """Add new budget for user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_budgets (user_id, category, budget_limit, current_spent, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (user_id, category, budget_limit))
                return True
        except Exception as e:
            logger.error(f"Error adding budget for user {user_id}: {e}")
            return False
    
    def update_budget_spending(self, user_id: int, category: str, amount: float) -> bool:
        """Update current spending for a budget"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_budgets 
                    SET current_spent = current_spent + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND category = ? AND is_active = 1
                """, (amount, user_id, category))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating budget spending for user {user_id}: {e}")
            return False
    
    def reset_budgets_monthly(self, user_id: int) -> bool:
        """Reset all budgets for new month"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_budgets 
                    SET current_spent = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
                return True
        except Exception as e:
            logger.error(f"Error resetting budgets for user {user_id}: {e}")
            return False
    
    def get_user_data_count(self, user_id: int) -> int:
        """Get user's data count for comparison"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT data_count FROM users WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                return row[0] if row and row[0] else 0
        except Exception as e:
            logger.error(f"Error getting data count for user {user_id}: {e}")
            return 0
    
    def update_user_data_count(self, user_id: int, count: int) -> bool:
        """Update user's data count"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET data_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (count, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating data count for user {user_id}: {e}")
            return False
    
    def get_auto_refresh_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's auto refresh settings"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT enabled, frequency, last_refresh, next_refresh
                    FROM finance_auto_refresh 
                    WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'enabled': bool(row[0]),
                        'frequency': row[1],
                        'last_refresh': row[2],
                        'next_refresh': row[3]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting auto refresh settings for user {user_id}: {e}")
            return None
    
    def set_auto_refresh_settings(self, user_id: int, enabled: bool, frequency: str = None) -> bool:
        """Set user's auto refresh settings"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if enabled:
                    cursor.execute("""
                        INSERT OR REPLACE INTO finance_auto_refresh 
                        (user_id, enabled, frequency, last_refresh, next_refresh, created_at, updated_at)
                        VALUES (?, 1, ?, CURRENT_TIMESTAMP, 
                                datetime('now', '+1 hour'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (user_id, frequency))
                else:
                    cursor.execute("""
                        UPDATE finance_auto_refresh 
                        SET enabled = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (user_id,))
                return True
        except Exception as e:
            logger.error(f"Error setting auto refresh for user {user_id}: {e}")
            return False
