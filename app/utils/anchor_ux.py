"""
Anchor-UX system for Teo bot
Manages single anchor message, session states, and navigation
"""
import logging
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class InputType(Enum):
    """Types of input that bot can await"""
    TEXT = "text"
    URL = "url"
    NUMBER = "number"
    DATE = "date"
    MONTH = "month"
    CURRENCY = "currency"
    TIME = "time"


@dataclass
class AwaitingInput:
    """Represents awaiting input state"""
    type: InputType
    hint: str
    ttl: int  # Time to live in seconds
    created_at: datetime
    context: Dict[str, Any] = None
    
    def is_expired(self) -> bool:
        """Check if awaiting input has expired"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['type'] = self.type.value
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AwaitingInput':
        """Create from dictionary"""
        data['type'] = InputType(data['type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class ScreenState:
    """Represents a screen state"""
    screen_id: str
    params: Dict[str, Any]
    title: str
    content: str
    status: str
    keyboard: List[List[Dict[str, str]]]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScreenState':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class UserSession:
    """Represents user session with anchor message"""
    user_id: int
    chat_id: int
    anchor_message_id: Optional[int]
    current_screen: Optional[ScreenState]
    awaiting_input: Optional[AwaitingInput]
    history_stack: List[ScreenState]
    last_activity: datetime
    nonce: str  # For idempotency
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['current_screen'] = self.current_screen.to_dict() if self.current_screen else None
        data['awaiting_input'] = self.awaiting_input.to_dict() if self.awaiting_input else None
        data['history_stack'] = [screen.to_dict() for screen in self.history_stack]
        data['last_activity'] = self.last_activity.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create from dictionary"""
        data['current_screen'] = ScreenState.from_dict(data['current_screen']) if data['current_screen'] else None
        data['awaiting_input'] = AwaitingInput.from_dict(data['awaiting_input']) if data['awaiting_input'] else None
        data['history_stack'] = [ScreenState.from_dict(screen) for screen in data['history_stack']]
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        return cls(**data)


class AnchorUXManager:
    """Manages Anchor-UX system for all users"""
    
    def __init__(self):
        self.sessions: Dict[Tuple[int, int], UserSession] = {}  # (user_id, chat_id) -> session
        self.callback_handlers: Dict[str, callable] = {}
        self.input_validators: Dict[InputType, callable] = {}
        self.screen_builders: Dict[str, callable] = {}
        
        # Register default input validators
        self._register_default_validators()
    
    def _register_default_validators(self):
        """Register default input validators"""
        import re
        
        def validate_url(text: str) -> Tuple[bool, str]:
            """Validate URL input"""
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if url_pattern.match(text):
                return True, ""
            return False, "Неверный формат URL. Пример: https://docs.google.com/spreadsheets/d/..."
        
        def validate_number(text: str) -> Tuple[bool, str]:
            """Validate number input"""
            try:
                float(text.replace(',', '.'))
                return True, ""
            except ValueError:
                return False, "Введите число. Пример: 1000 или 1000.50"
        
        def validate_date(text: str) -> Tuple[bool, str]:
            """Validate date input (YYYY-MM-DD)"""
            try:
                datetime.strptime(text, '%Y-%m-%d')
                return True, ""
            except ValueError:
                return False, "Формат даты: YYYY-MM-DD. Пример: 2024-12-31"
        
        def validate_month(text: str) -> Tuple[bool, str]:
            """Validate month input (YYYY-MM)"""
            try:
                datetime.strptime(text, '%Y-%m')
                return True, ""
            except ValueError:
                return False, "Формат месяца: YYYY-MM. Пример: 2024-12"
        
        def validate_time(text: str) -> Tuple[bool, str]:
            """Validate time input (HH:MM)"""
            try:
                datetime.strptime(text, '%H:%M')
                return True, ""
            except ValueError:
                return False, "Формат времени: HH:MM. Пример: 09:30"
        
        self.input_validators[InputType.URL] = validate_url
        self.input_validators[InputType.NUMBER] = validate_number
        self.input_validators[InputType.DATE] = validate_date
        self.input_validators[InputType.MONTH] = validate_month
        self.input_validators[InputType.TIME] = validate_time
        self.input_validators[InputType.TEXT] = lambda text: (True, "")  # Always valid
        self.input_validators[InputType.CURRENCY] = lambda text: (True, "")  # Always valid for now
    
    def get_session(self, user_id: int, chat_id: int) -> UserSession:
        """Get or create user session"""
        key = (user_id, chat_id)
        if key not in self.sessions:
            self.sessions[key] = UserSession(
                user_id=user_id,
                chat_id=chat_id,
                anchor_message_id=None,
                current_screen=None,
                awaiting_input=None,
                history_stack=[],
                last_activity=datetime.now(),
                nonce=self._generate_nonce()
            )
        return self.sessions[key]
    
    def _generate_nonce(self) -> str:
        """Generate unique nonce for idempotency"""
        return hashlib.md5(f"{time.time()}_{id(self)}".encode()).hexdigest()[:8]
    
    def update_session_activity(self, user_id: int, chat_id: int):
        """Update session last activity"""
        session = self.get_session(user_id, chat_id)
        session.last_activity = datetime.now()
    
    def set_anchor_message(self, user_id: int, chat_id: int, message_id: int):
        """Set anchor message ID for user"""
        session = self.get_session(user_id, chat_id)
        session.anchor_message_id = message_id
    
    def get_anchor_message_id(self, user_id: int, chat_id: int) -> Optional[int]:
        """Get anchor message ID for user"""
        session = self.get_session(user_id, chat_id)
        return session.anchor_message_id
    
    def set_current_screen(self, user_id: int, chat_id: int, screen: ScreenState):
        """Set current screen and add to history"""
        session = self.get_session(user_id, chat_id)
        
        # Add current screen to history if it exists
        if session.current_screen:
            session.history_stack.append(session.current_screen)
            # Keep only last 10 screens in history
            if len(session.history_stack) > 10:
                session.history_stack.pop(0)
        
        session.current_screen = screen
        session.last_activity = datetime.now()
    
    def get_current_screen(self, user_id: int, chat_id: int) -> Optional[ScreenState]:
        """Get current screen"""
        session = self.get_session(user_id, chat_id)
        return session.current_screen
    
    def go_back(self, user_id: int, chat_id: int) -> Optional[ScreenState]:
        """Go back to previous screen"""
        session = self.get_session(user_id, chat_id)
        
        if session.history_stack:
            previous_screen = session.history_stack.pop()
            session.current_screen = previous_screen
            session.last_activity = datetime.now()
            return previous_screen
        
        return None
    
    def set_awaiting_input(self, user_id: int, chat_id: int, input_type: InputType, 
                          hint: str, ttl: int = 300, context: Dict[str, Any] = None):
        """Set awaiting input state"""
        session = self.get_session(user_id, chat_id)
        session.awaiting_input = AwaitingInput(
            type=input_type,
            hint=hint,
            ttl=ttl,
            created_at=datetime.now(),
            context=context or {}
        )
        session.last_activity = datetime.now()
    
    def clear_awaiting_input(self, user_id: int, chat_id: int):
        """Clear awaiting input state"""
        session = self.get_session(user_id, chat_id)
        session.awaiting_input = None
        session.last_activity = datetime.now()
    
    def get_awaiting_input(self, user_id: int, chat_id: int) -> Optional[AwaitingInput]:
        """Get awaiting input state"""
        session = self.get_session(user_id, chat_id)
        return session.awaiting_input
    
    def validate_input(self, input_type: InputType, text: str) -> Tuple[bool, str]:
        """Validate input text"""
        validator = self.input_validators.get(input_type)
        if validator:
            return validator(text)
        return True, ""
    
    def register_callback_handler(self, action: str, handler: callable):
        """Register callback handler"""
        self.callback_handlers[action] = handler
    
    def register_screen_builder(self, screen_id: str, builder: callable):
        """Register screen builder"""
        self.screen_builders[screen_id] = builder
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            action: str, params: Dict[str, Any] = None) -> bool:
        """Handle callback with registered handler"""
        handler = self.callback_handlers.get(action)
        if handler:
            await handler(update, context, params or {})
            return True
        return False
    
    async def build_screen(self, screen_id: str, user_id: int, chat_id: int, 
                          params: Dict[str, Any] = None) -> ScreenState:
        """Build screen using registered builder"""
        builder = self.screen_builders.get(screen_id)
        if builder:
            return await builder(user_id, chat_id, params or {})
        
        # Default screen if no builder registered
        return ScreenState(
            screen_id=screen_id,
            params=params or {},
            title=f"Экран {screen_id}",
            content="Экран в разработке",
            status="",
            keyboard=[],
            created_at=datetime.now()
        )
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired sessions"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_keys = []
        
        for key, session in self.sessions.items():
            if session.last_activity < cutoff_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.sessions[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired sessions")


class AnchorKeyboardBuilder:
    """Builder for Anchor-UX keyboards with standard navigation"""
    
    @staticmethod
    def add_navigation_buttons(keyboard: List[List[Dict[str, str]]], 
                              can_go_back: bool = True) -> List[List[Dict[str, str]]]:
        """Add standard navigation buttons (Back and Main Menu)"""
        nav_row = []
        
        if can_go_back:
            nav_row.append({"text": "🔙 Назад", "callback_data": "nav_back"})
        
        nav_row.append({"text": "🏠 Главное меню", "callback_data": "nav_main"})
        
        if nav_row:
            keyboard.append(nav_row)
        
        return keyboard
    
    @staticmethod
    def create_action_keyboard(actions: List[Dict[str, str]], 
                              can_go_back: bool = True) -> List[List[Dict[str, str]]]:
        """Create keyboard with action buttons and navigation"""
        keyboard = []
        
        # Add action buttons (max 2 per row)
        for i in range(0, len(actions), 2):
            row = actions[i:i+2]
            keyboard.append(row)
        
        # Add navigation buttons
        return AnchorKeyboardBuilder.add_navigation_buttons(keyboard, can_go_back)
    
    @staticmethod
    def create_pagination_keyboard(current_page: int, total_pages: int, 
                                  page_action: str, can_go_back: bool = True) -> List[List[Dict[str, str]]]:
        """Create pagination keyboard"""
        keyboard = []
        
        # Pagination row
        pagination_row = []
        
        if current_page > 1:
            pagination_row.append({
                "text": "‹ Пред", 
                "callback_data": f"{page_action}_page_{current_page - 1}"
            })
        
        pagination_row.append({
            "text": f"Стр. {current_page}/{total_pages}", 
            "callback_data": "no_action"
        })
        
        if current_page < total_pages:
            pagination_row.append({
                "text": "След ›", 
                "callback_data": f"{page_action}_page_{current_page + 1}"
            })
        
        keyboard.append(pagination_row)
        
        # Add navigation buttons
        return AnchorKeyboardBuilder.add_navigation_buttons(keyboard, can_go_back)
    
    @staticmethod
    def create_confirmation_keyboard(confirm_action: str, cancel_action: str = "nav_back") -> List[List[Dict[str, str]]]:
        """Create confirmation keyboard"""
        keyboard = [
            [
                {"text": "✅ Да, подтвердить", "callback_data": confirm_action},
                {"text": "❌ Отмена", "callback_data": cancel_action}
            ]
        ]
        
        return AnchorKeyboardBuilder.add_navigation_buttons(keyboard, True)


class AnchorMessageBuilder:
    """Builder for Anchor-UX messages with standard structure"""
    
    @staticmethod
    def build_screen_message(title: str, content: str, status: str = "", 
                           awaiting_input: Optional[AwaitingInput] = None) -> str:
        """Build complete screen message"""
        message_parts = []
        
        # Header with awaiting input indicator
        if awaiting_input:
            message_parts.append(f"⏳ **Жду: {awaiting_input.hint}**")
            message_parts.append("")  # Empty line
        
        # Title
        message_parts.append(f"**{title}**")
        message_parts.append("")  # Empty line
        
        # Content
        message_parts.append(content)
        
        # Status
        if status:
            message_parts.append("")  # Empty line
            message_parts.append(f"_{status}_")
        
        return "\n".join(message_parts)
    
    @staticmethod
    def build_awaiting_input_message(input_type: InputType, hint: str, 
                                   example: str = "") -> str:
        """Build message for awaiting input state"""
        message_parts = [
            f"⏳ **Жду: {hint}**",
            "",
            "Отправьте сообщение с нужными данными."
        ]
        
        if example:
            message_parts.append("")
            message_parts.append(f"**Пример:** {example}")
        
        return "\n".join(message_parts)
    
    @staticmethod
    def build_error_message(error: str, suggestion: str = "") -> str:
        """Build error message"""
        message_parts = [
            f"❌ **Ошибка:** {error}"
        ]
        
        if suggestion:
            message_parts.append("")
            message_parts.append(f"💡 **Совет:** {suggestion}")
        
        return "\n".join(message_parts)
    
    @staticmethod
    def build_success_message(message: str, action: str = "") -> str:
        """Build success message"""
        message_parts = [
            f"✅ **{message}**"
        ]
        
        if action:
            message_parts.append("")
            message_parts.append(f"🎯 **Следующий шаг:** {action}")
        
        return "\n".join(message_parts)


# Global instance
anchor_ux_manager = AnchorUXManager()





