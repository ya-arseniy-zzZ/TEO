"""
Interactive settings module for Teo bot
Provides button-based selection interfaces with pagination
"""
from typing import List, Dict, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Russian cities with their proper names
RUSSIAN_CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград",
    "Краснодар", "Саратов", "Тюмень", "Тольятти", "Ижевск",
    "Барнаул", "Ульяновск", "Иркутск", "Хабаровск", "Ярославль",
    "Владивосток", "Махачкала", "Томск", "Оренбург", "Кемерово",
    "Новокузнецк", "Рязань", "Астрахань", "Пенза", "Липецк"
]

# Russian timezones
RUSSIAN_TIMEZONES = [
    ("Europe/Moscow", "Москва (UTC+3)"),
    ("Europe/Kaliningrad", "Калининград (UTC+2)"),
    ("Asia/Yekaterinburg", "Екатеринбург (UTC+5)"),
    ("Asia/Novosibirsk", "Новосибирск (UTC+7)"),
    ("Asia/Krasnoyarsk", "Красноярск (UTC+7)"),
    ("Asia/Irkutsk", "Иркутск (UTC+8)"),
    ("Asia/Yakutsk", "Якутск (UTC+9)"),
    ("Asia/Vladivostok", "Владивосток (UTC+10)"),
    ("Asia/Magadan", "Магадан (UTC+11)"),
    ("Asia/Kamchatka", "Камчатка (UTC+12)")
]

# Common notification times - starting at 8 AM with hourly intervals
NOTIFICATION_TIMES = [
    "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", 
    "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"
]


class InteractiveSettings:
    """Handles interactive settings with pagination"""
    
    @staticmethod
    def create_city_keyboard(page: int = 0) -> Tuple[InlineKeyboardMarkup, bool]:
        """
        Create paginated city selection keyboard
        
        Args:
            page: Current page number (0-based)
            
        Returns:
            Tuple of (keyboard, has_next_page)
        """
        items_per_page = 4  # Leave room for navigation buttons
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        cities_page = RUSSIAN_CITIES[start_idx:end_idx]
        has_next = end_idx < len(RUSSIAN_CITIES)
        has_prev = page > 0
        
        keyboard = []
        
        # Add city buttons (2 per row)
        for i in range(0, len(cities_page), 2):
            row = []
            row.append(InlineKeyboardButton(cities_page[i], callback_data=f'select_city_{cities_page[i]}'))
            if i + 1 < len(cities_page):
                row.append(InlineKeyboardButton(cities_page[i + 1], callback_data=f'select_city_{cities_page[i + 1]}'))
            keyboard.append(row)
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'city_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'city_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Action buttons
        keyboard.append([
            InlineKeyboardButton("✏️ Ввести свой город", callback_data='custom_city_input'),
            InlineKeyboardButton("🔙 Назад", callback_data='settings')
        ])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def create_timezone_keyboard(page: int = 0) -> Tuple[InlineKeyboardMarkup, bool]:
        """
        Create paginated timezone selection keyboard
        
        Args:
            page: Current page number (0-based)
            
        Returns:
            Tuple of (keyboard, has_next_page)
        """
        items_per_page = 4
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        timezones_page = RUSSIAN_TIMEZONES[start_idx:end_idx]
        has_next = end_idx < len(RUSSIAN_TIMEZONES)
        has_prev = page > 0
        
        keyboard = []
        
        # Add timezone buttons (1 per row for readability)
        for tz_id, tz_name in timezones_page:
            keyboard.append([InlineKeyboardButton(tz_name, callback_data=f'select_timezone_{tz_id}')])
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'timezone_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'timezone_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='settings')])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def create_time_keyboard(page: int = 0) -> Tuple[InlineKeyboardMarkup, bool]:
        """
        Create paginated notification time selection keyboard
        
        Args:
            page: Current page number (0-based)
            
        Returns:
            Tuple of (keyboard, has_next_page)
        """
        items_per_page = 4
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        times_page = NOTIFICATION_TIMES[start_idx:end_idx]
        has_next = end_idx < len(NOTIFICATION_TIMES)
        has_prev = page > 0
        
        keyboard = []
        
        # Add time buttons (2 per row)
        for i in range(0, len(times_page), 2):
            row = []
            row.append(InlineKeyboardButton(f"🕐 {times_page[i]}", callback_data=f'select_time_{times_page[i]}'))
            if i + 1 < len(times_page):
                row.append(InlineKeyboardButton(f"🕐 {times_page[i + 1]}", callback_data=f'select_time_{times_page[i + 1]}'))
            keyboard.append(row)
        
        # Navigation row
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'time_page_{page - 1}'))
        if has_next:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f'time_page_{page + 1}'))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Action buttons
        keyboard.append([
            InlineKeyboardButton("✏️ Ввести своё время", callback_data='custom_time_input'),
            InlineKeyboardButton("🔙 К уведомлениям", callback_data='notifications_menu')
        ])
        
        return InlineKeyboardMarkup(keyboard), has_next
    
    @staticmethod
    def get_city_page_count() -> int:
        """Get total number of city pages"""
        return (len(RUSSIAN_CITIES) + 3) // 4  # 4 items per page
    
    @staticmethod
    def get_timezone_page_count() -> int:
        """Get total number of timezone pages"""
        return (len(RUSSIAN_TIMEZONES) + 3) // 4  # 4 items per page
    
    @staticmethod
    def get_time_page_count() -> int:
        """Get total number of time pages"""
        return (len(NOTIFICATION_TIMES) + 3) // 4  # 4 items per page
    
    @staticmethod
    def find_timezone_name(timezone_id: str) -> str:
        """Find timezone display name by ID"""
        for tz_id, tz_name in RUSSIAN_TIMEZONES:
            if tz_id == timezone_id:
                return tz_name
        return timezone_id  # Fallback to ID if not found
    
    @staticmethod
    def create_custom_input_keyboard(input_type: str) -> InlineKeyboardMarkup:
        """
        Create keyboard for custom input
        
        Args:
            input_type: Type of input ('city' or 'time')
            
        Returns:
            InlineKeyboardMarkup
        """
        if input_type == 'city':
            back_callback = 'city_page_0'
            back_text = "🔙 К выбору города"
        elif input_type == 'time':
            back_callback = 'time_page_0'
            back_text = "🔙 К выбору времени"
        else:
            back_callback = 'settings'
            back_text = "🔙 Назад"
        
        keyboard = [
            [InlineKeyboardButton(back_text, callback_data=back_callback)],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    

