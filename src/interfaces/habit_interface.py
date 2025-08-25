"""
Interactive habit interface for Teo bot
Provides button-based habit management with pagination
"""
from typing import List, Dict, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta

# Common reminder times for habits - starting at 8 AM with hourly intervals
HABIT_TIMES = [
    "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", 
    "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"
]

# Days of week in Russian
DAYS_RUSSIAN = {
    "monday": "Пн", "tuesday": "Вт", "wednesday": "Ср", 
    "thursday": "Чт", "friday": "Пт", "saturday": "Сб", "sunday": "Вс"
}

# Common habit suggestions
HABIT_SUGGESTIONS = [
    "Выпить стакан воды", "Сделать зарядку", "Почитать книгу", "Медитировать",
    "Сделать 50 отжиманий", "Выучить 10 новых слов", "Написать в дневнике", "Принять витамины"
]


class HabitInterface:
    """Handles interactive habit management interfaces"""
    
    @staticmethod
    def create_main_habits_menu() -> InlineKeyboardMarkup:
        """Create main habits menu"""
        keyboard = [
            [InlineKeyboardButton("📋 Мои привычки", callback_data='view_habits'),
             InlineKeyboardButton("➕ Новая привычка", callback_data='create_habit')],
            [InlineKeyboardButton("📊 Статистика", callback_data='habit_stats'),
             InlineKeyboardButton("⚙️ Управление", callback_data='manage_habits')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_habits_list_keyboard(habits: List[Dict], page: int = 0, show_completion: bool = True) -> Tuple[InlineKeyboardMarkup, bool]:
        """
        Create paginated habits list keyboard
        
        Args:
            habits: List of user habits
            page: Current page number
            show_completion: Whether to show completion buttons
            
        Returns:
            Tuple of (keyboard, has_next_page)
        """
        items_per_page = 3  # 3 habits per page to leave room for buttons
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        habits_page = habits[start_idx:end_idx]
        has_next = end_idx < len(habits)
        has_prev = page > 0
        
        keyboard = []
        
        # Import here to avoid circular imports
        from database import DatabaseManager
        db = DatabaseManager()
        
        # Add habit buttons
        for habit in habits_page:
            status = "✅" if db.is_habit_completed_today(habit['habit_id']) else "⏳"
            habit_name = f"{status} {habit['name']}"
            
            if show_completion and not db.is_habit_completed_today(habit['habit_id']):
                # Show completion button for incomplete habits
                keyboard.append([
                    InlineKeyboardButton(habit_name, callback_data=f'habit_details_{habit["habit_id"]}'),
                    InlineKeyboardButton("✅ Готово", callback_data=f'complete_habit_{habit["habit_id"]}')
                ])
            else:
                # Just show habit details
                keyboard.append([
                    InlineKeyboardButton(habit_name, callback_data=f'habit_details_{habit["habit_id"]}')
                ])
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'habits_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'habits_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def create_habit_details_keyboard(habit: Dict) -> InlineKeyboardMarkup:
        """Create keyboard for habit details"""
        keyboard = []
        
        # Import here to avoid circular imports
        from database import DatabaseManager
        db = DatabaseManager()
        
        # Completion button if not completed today
        if not db.is_habit_completed_today(habit['habit_id']):
            keyboard.append([InlineKeyboardButton("✅ Отметить выполненной", callback_data=f'complete_habit_{habit["habit_id"]}')])
        
        # Management buttons
        keyboard.append([
            InlineKeyboardButton("✏️ Редактировать", callback_data=f'edit_habit_{habit["habit_id"]}'),
            InlineKeyboardButton("🗑 Удалить", callback_data=f'delete_habit_{habit["habit_id"]}')
        ])
        
        # Navigation
        keyboard.append([
            InlineKeyboardButton("📋 К списку привычек", callback_data='view_habits'),
            InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_habit_suggestions_keyboard(page: int = 0) -> Tuple[InlineKeyboardMarkup, bool]:
        """Create habit suggestions keyboard with pagination"""
        items_per_page = 4
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        suggestions_page = HABIT_SUGGESTIONS[start_idx:end_idx]
        has_next = end_idx < len(HABIT_SUGGESTIONS)
        has_prev = page > 0
        
        keyboard = []
        
        # Add suggestion buttons (2 per row)
        for i in range(0, len(suggestions_page), 2):
            row = []
            row.append(InlineKeyboardButton(suggestions_page[i], callback_data=f'suggest_habit_{suggestions_page[i]}'))
            if i + 1 < len(suggestions_page):
                row.append(InlineKeyboardButton(suggestions_page[i + 1], callback_data=f'suggest_habit_{suggestions_page[i + 1]}'))
            keyboard.append(row)
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'suggestions_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'suggestions_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Action buttons
        keyboard.append([
            InlineKeyboardButton("✏️ Своя привычка", callback_data='custom_habit_input'),
            InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')
        ])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def create_time_selection_keyboard(page: int = 0) -> Tuple[InlineKeyboardMarkup, bool]:
        """Create time selection keyboard for habits"""
        items_per_page = 4
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        times_page = HABIT_TIMES[start_idx:end_idx]
        has_next = end_idx < len(HABIT_TIMES)
        has_prev = page > 0
        
        keyboard = []
        
        # Add time buttons (2 per row)
        for i in range(0, len(times_page), 2):
            row = []
            row.append(InlineKeyboardButton(f"🕐 {times_page[i]}", callback_data=f'habit_time_{times_page[i]}'))
            if i + 1 < len(times_page):
                row.append(InlineKeyboardButton(f"🕐 {times_page[i + 1]}", callback_data=f'habit_time_{times_page[i + 1]}'))
            keyboard.append(row)
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'habit_time_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'habit_time_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='create_habit')])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def create_days_selection_keyboard(selected_days: List[str] = None) -> InlineKeyboardMarkup:
        """Create days of week selection keyboard"""
        selected_days = selected_days or []
        
        keyboard = []
        
        # Add day buttons (4 in first row, 3 in second)
        first_row = []
        second_row = []
        
        days_full = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        for i, day in enumerate(days_full):
            day_text = DAYS_RUSSIAN[day]
            if day in selected_days:
                day_text = f"✅ {day_text}"
            
            button = InlineKeyboardButton(day_text, callback_data=f'toggle_day_{day}')
            
            if i < 4:
                first_row.append(button)
            else:
                second_row.append(button)
        
        keyboard.append(first_row)
        keyboard.append(second_row)
        
        # Quick select buttons
        keyboard.append([
            InlineKeyboardButton("📅 Будни", callback_data='select_weekdays'),
            InlineKeyboardButton("🎯 Каждый день", callback_data='select_all_days')
        ])
        
        # Navigation
        keyboard.append([
            InlineKeyboardButton("✅ Готово", callback_data='days_selection_done'),
            InlineKeyboardButton("🔙 Назад", callback_data='create_habit')
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_management_keyboard(habits: List[Dict], page: int = 0) -> Tuple[InlineKeyboardMarkup, bool]:
        """Create habit management keyboard"""
        items_per_page = 3
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        habits_page = habits[start_idx:end_idx]
        has_next = end_idx < len(habits)
        has_prev = page > 0
        
        keyboard = []
        
        # Add habit management buttons
        for habit in habits_page:
            keyboard.append([
                InlineKeyboardButton(f"✏️ {habit['name']}", callback_data=f'edit_habit_{habit["habit_id"]}'),
                InlineKeyboardButton("🗑", callback_data=f'delete_habit_{habit["habit_id"]}')
            ])
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'manage_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'manage_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def create_confirmation_keyboard(action: str, habit_id: str) -> InlineKeyboardMarkup:
        """Create confirmation keyboard for destructive actions"""
        keyboard = [
            [InlineKeyboardButton("✅ Да, подтверждаю", callback_data=f'confirm_{action}_{habit_id}')],
            [InlineKeyboardButton("❌ Отмена", callback_data=f'habit_details_{habit_id}')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_habit_time_keyboard(page: int = 0) -> Tuple[InlineKeyboardMarkup, bool]:
        """
        Create paginated habit time selection keyboard
        
        Args:
            page: Current page number (0-based)
            
        Returns:
            Tuple of (keyboard, has_next_page)
        """
        items_per_page = 4  # 4 times per page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        times_page = HABIT_TIMES[start_idx:end_idx]
        has_next = end_idx < len(HABIT_TIMES)
        has_prev = page > 0
        
        keyboard = []
        
        # Add time buttons (2 per row)
        for i in range(0, len(times_page), 2):
            row = []
            row.append(InlineKeyboardButton(f"🕐 {times_page[i]}", callback_data=f'select_habit_time_{times_page[i]}'))
            if i + 1 < len(times_page):
                row.append(InlineKeyboardButton(f"🕐 {times_page[i + 1]}", callback_data=f'select_habit_time_{times_page[i + 1]}'))
            keyboard.append(row)
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'habit_time_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'habit_time_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Action buttons
        keyboard.append([
            InlineKeyboardButton("✏️ Ввести своё время", callback_data='custom_habit_time_input'),
            InlineKeyboardButton("🔙 К привычкам", callback_data='create_habit')
        ])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def create_custom_habit_time_keyboard() -> InlineKeyboardMarkup:
        """
        Create keyboard for custom habit time input
        
        Returns:
            InlineKeyboardMarkup
        """
        keyboard = [
            [InlineKeyboardButton("🔙 К выбору времени", callback_data='habit_time_page_0')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_habit_time_page_count() -> int:
        """Get total number of habit time pages"""
        return (len(HABIT_TIMES) + 3) // 4  # 4 items per page
    
    @staticmethod
    def format_habit_details(habit: Dict) -> str:
        """Format habit details for display"""
        # Import here to avoid circular imports
        from database import DatabaseManager
        db = DatabaseManager()
        
        status = "✅ Выполнена" if db.is_habit_completed_today(habit['habit_id']) else "⏳ Ожидает выполнения"
        
        # Calculate streak and completion rate
        completions = db.get_habit_completions(habit['habit_id'], 30)
        streak = HabitInterface._calculate_streak(completions)
        
        # Calculate completion rate for last week
        week_completions = [c for c in completions if c >= (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")]
        expected_days = len(habit['reminder_days'])
        completion_rate = (len(week_completions) / min(expected_days, 7) * 100) if expected_days > 0 else 0
        
        days_text = ", ".join([DAYS_RUSSIAN[day] for day in habit['reminder_days']])
        
        message = f"""📋 **{habit['name']}**

{status}

📝 **Описание:** {habit['description'] or "Не указано"}
⏰ **Время напоминания:** {habit['reminder_time']}
📅 **Дни:** {days_text}
🔥 **Текущая серия:** {streak} дн.
📊 **За неделю:** {completion_rate:.1f}%
📆 **Создана:** {habit['created_at'][:10]}"""
        
        return message
    
    @staticmethod
    def _calculate_streak(completions: List[str]) -> int:
        """Calculate current completion streak"""
        if not completions:
            return 0
        
        # Sort completions and calculate streak from today backwards
        sorted_completions = sorted(completions, reverse=True)
        today = datetime.now()
        streak = 0
        
        for i, completion_date in enumerate(sorted_completions):
            expected_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if completion_date == expected_date:
                streak += 1
            else:
                break
        
        return streak
    
    @staticmethod
    def get_page_count(items_count: int, items_per_page: int = 3) -> int:
        """Calculate total pages needed"""
        return (items_count + items_per_page - 1) // items_per_page
