"""
Error handling utilities for Teo bot
Centralized error handling and logging
"""
import logging
from typing import Optional, Callable, Any
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .keyboards import KeyboardBuilder
from .messages import MessageBuilder

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for Teo bot"""
    
    @staticmethod
    async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          error: Exception, error_type: str = "general") -> None:
        """
        Handle errors and send appropriate error message to user
        
        Args:
            update: Telegram update object
            context: Telegram context object
            error: The exception that occurred
            error_type: Type of error for specific handling
        """
        # Log the error
        logger.error(f"Error in {error_type}: {error}", exc_info=True)
        
        # Get error message
        error_msg = MessageBuilder.error_message(error_type)
        
        # Create keyboard based on context
        keyboard = KeyboardBuilder.error_back()
        
        # Send error message
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=error_msg,
                    reply_markup=keyboard
                )
            elif update.message:
                await update.message.reply_text(
                    text=error_msg,
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    @staticmethod
    def safe_execute(func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Safely execute a function and handle any exceptions
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if error occurred
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in safe_execute for {func.__name__}: {e}")
            return None
    
    @staticmethod
    async def safe_async_execute(func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Safely execute an async function and handle any exceptions
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if error occurred
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in safe_async_execute for {func.__name__}: {e}")
            return None
    
    @staticmethod
    def validate_input(value: Any, expected_type: type, 
                      min_length: Optional[int] = None,
                      max_length: Optional[int] = None) -> bool:
        """
        Validate input parameters
        
        Args:
            value: Value to validate
            expected_type: Expected type
            min_length: Minimum length (for strings)
            max_length: Maximum length (for strings)
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check type
            if not isinstance(value, expected_type):
                return False
            
            # Check length for strings
            if isinstance(value, str):
                if min_length and len(value) < min_length:
                    return False
                if max_length and len(value) > max_length:
                    return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def log_operation(operation: str, user_id: Optional[int] = None, 
                     details: Optional[str] = None) -> None:
        """
        Log operation for debugging and monitoring
        
        Args:
            operation: Operation name
            user_id: User ID if applicable
            details: Additional details
        """
        log_msg = f"Operation: {operation}"
        if user_id:
            log_msg += f" | User: {user_id}"
        if details:
            log_msg += f" | Details: {details}"
        
        logger.info(log_msg)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class ServiceError(Exception):
    """Custom exception for service errors"""
    pass


class DatabaseError(Exception):
    """Custom exception for database errors"""
    pass
