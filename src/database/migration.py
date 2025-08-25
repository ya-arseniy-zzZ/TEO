"""
Migration system to convert existing file-based data to SQLite database
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)


class DataMigration:
    """Handles migration from file storage to database"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def migrate_all_data(self) -> bool:
        """Migrate all existing data to database"""
        try:
            logger.info("Starting data migration...")
            
            # Migrate habits data
            self.migrate_habits_data()
            
            # Note: user_settings and other data are in-memory only,
            # so we'll initialize with defaults in the database
            
            logger.info("Data migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return False
    
    def migrate_habits_data(self) -> None:
        """Migrate habits from JSON file to database"""
        habits_file = "user_habits.json"
        
        if not os.path.exists(habits_file):
            logger.info("No existing habits file found, skipping habits migration")
            return
        
        try:
            with open(habits_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            habits_data = data.get('habits', [])
            migrated_count = 0
            
            for habit_data in habits_data:
                # Extract habit information
                habit_id = habit_data.get('habit_id')
                user_id = habit_data.get('user_id')
                name = habit_data.get('name', '')
                description = habit_data.get('description', '')
                reminder_time = habit_data.get('reminder_time', '09:00')
                reminder_days = habit_data.get('reminder_days', [])
                is_active = habit_data.get('is_active', True)
                completions = habit_data.get('completions', [])
                
                if not habit_id or not user_id or not name:
                    logger.warning(f"Skipping invalid habit data: {habit_data}")
                    continue
                
                # Create user if not exists
                self.db.create_or_update_user(user_id)
                
                # Create habit
                success = self.db.create_habit(
                    habit_id=habit_id,
                    user_id=user_id,
                    name=name,
                    description=description,
                    reminder_time=reminder_time,
                    reminder_days=reminder_days
                )
                
                if success:
                    # Set active status if different from default
                    if not is_active:
                        self.db.update_habit(habit_id, is_active=False)
                    
                    # Migrate completions
                    for completion_date in completions:
                        self.db.mark_habit_completed(habit_id, user_id, completion_date)
                    
                    migrated_count += 1
                    logger.info(f"Migrated habit: {name} for user {user_id}")
                else:
                    logger.error(f"Failed to migrate habit: {name} for user {user_id}")
            
            logger.info(f"Successfully migrated {migrated_count} habits")
            
            # Backup original file
            backup_file = f"{habits_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(habits_file, backup_file)
            logger.info(f"Original habits file backed up as: {backup_file}")
            
        except Exception as e:
            logger.error(f"Error migrating habits data: {e}")
    
    def initialize_default_users(self, user_ids: list) -> None:
        """Initialize default users in database (for testing)"""
        for user_id in user_ids:
            self.db.create_or_update_user(user_id, f"user_{user_id}", f"User {user_id}")
            logger.info(f"Initialized default user: {user_id}")
    
    def verify_migration(self) -> Dict[str, int]:
        """Verify migration results"""
        stats = self.db.get_database_stats()
        logger.info(f"Migration verification - Database stats: {stats}")
        return stats
    
    def migrate_schema(self) -> None:
        """Migrate database schema (add new columns, tables, etc.)"""
        try:
            logger.info("Starting schema migration...")
            
            # Add google_sheets_url column to users table if it doesn't exist
            self.db.add_column_if_not_exists('users', 'google_sheets_url', 'TEXT')
            
            # Add single message interface columns
            self.db.add_column_if_not_exists('users', 'main_message_id', 'INTEGER')
            self.db.add_column_if_not_exists('users', 'current_state', 'TEXT')
            
            logger.info("Schema migration completed successfully")
            
        except Exception as e:
            logger.error(f"Error during schema migration: {e}")


def run_migration():
    """Run the migration process"""
    migration = DataMigration()
    
    # Check if migration is needed
    stats = migration.db.get_database_stats()
    if stats.get('active_users', 0) > 0:
        logger.info("Database already contains data, running schema migration only")
        migration.migrate_schema()
        return True
    
    # Run migration
    success = migration.migrate_all_data()
    
    if success:
        # Verify results
        final_stats = migration.verify_migration()
        logger.info(f"Migration completed. Final stats: {final_stats}")
    
    return success


def run_schema_migration():
    """Run schema migration only (for existing databases)"""
    migration = DataMigration()
    migration.migrate_schema()
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
