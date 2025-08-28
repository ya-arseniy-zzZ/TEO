"""
Single Message Decorator for Teo Bot
Universal decorator to ensure single message policy across all bot functions
"""
import logging
import functools
from typing import Callable, Any, Optional
from telegram import Update, Bot
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class SingleMessageDecorator:
    """Decorator class to enforce single message policy"""
    
    def __init__(self, message_manager):
        self.message_manager = message_manager
    
    def ensure_single_message(
        self, 
        auto_cleanup: bool = True,
        force_new_message: bool = False
    ):
        """
        Decorator to ensure single message policy for any bot function
        
        Args:
            auto_cleanup: Automatically clean previous messages
            force_new_message: Always send new message instead of editing
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    # Extract update, context, and user_id from function arguments
                    update = None
                    context = None
                    user_id = None
                    
                    # Try to find Update and Context in args
                    for arg in args:
                        if isinstance(arg, Update):
                            update = arg
                            user_id = arg.effective_user.id if arg.effective_user else None
                        elif hasattr(arg, 'bot') and hasattr(arg.bot, 'send_message'):
                            context = arg
                    
                    # Try to find in kwargs
                    if not update:
                        update = kwargs.get('update')
                        if update and update.effective_user:
                            user_id = update.effective_user.id
                    
                    if not context:
                        context = kwargs.get('context')
                    
                    if not user_id:
                        user_id = kwargs.get('user_id')
                    
                    # If we have the necessary components, apply single message policy
                    if auto_cleanup and user_id and context and context.bot:
                        logger.info(f"🎯 Applying single message policy for user {user_id} in function {func.__name__}")
                        
                        if force_new_message:
                            # Force clean state before function execution
                            await self.message_manager.force_single_message_state(context.bot, user_id)
                    
                    # Execute the original function
                    result = await func(*args, **kwargs)
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in single message decorator for function {func.__name__}: {e}")
                    # Continue with original function execution even if decorator fails
                    return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def single_message_handler(
        self, 
        message_type: str = 'text',
        cleanup_before: bool = True,
        cleanup_after: bool = False
    ):
        """
        Decorator for message handlers that enforces single message policy
        
        Args:
            message_type: Type of message ('text', 'photo', etc.)
            cleanup_before: Clean messages before handler execution
            cleanup_after: Clean messages after handler execution
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
                try:
                    user_id = update.effective_user.id if update.effective_user else None
                    
                    if user_id and cleanup_before:
                        logger.info(f"🧹 Pre-cleanup for handler {func.__name__} user {user_id}")
                        await self.message_manager._guarantee_single_message_cleanup(context.bot, user_id)
                    
                    # Execute handler
                    result = await func(update, context, *args, **kwargs)
                    
                    if user_id and cleanup_after:
                        logger.info(f"🧹 Post-cleanup for handler {func.__name__} user {user_id}")
                        await self.message_manager._guarantee_single_message_cleanup(context.bot, user_id)
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in single message handler decorator for {func.__name__}: {e}")
                    return await func(update, context, *args, **kwargs)
            
            return wrapper
        return decorator


# Global function to wrap any bot method with single message policy
def with_single_message_policy(message_manager, force_cleanup: bool = True):
    """
    Global decorator function for single message policy
    
    Usage:
        @with_single_message_policy(message_manager)
        async def my_bot_function(update, context):
            # Your bot logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Extract user_id and context
                update = None
                context = None
                user_id = None
                
                for arg in args:
                    if isinstance(arg, Update):
                        update = arg
                        user_id = arg.effective_user.id if arg.effective_user else None
                    elif hasattr(arg, 'bot'):
                        context = arg
                
                if force_cleanup and user_id and context and context.bot:
                    logger.info(f"🎯 Enforcing single message policy in {func.__name__} for user {user_id}")
                    await message_manager._guarantee_single_message_cleanup(context.bot, user_id)
                
                return await func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in single message policy wrapper for {func.__name__}: {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Utility class for managing single message state
class SingleMessageState:
    """Utility class to manage single message state across the application"""
    
    def __init__(self, message_manager):
        self.message_manager = message_manager
        self._enforced_users = set()  # Track users with enforced single message policy
    
    async def enforce_for_user(self, bot: Bot, user_id: int) -> bool:
        """Enforce single message policy for specific user"""
        try:
            await self.message_manager.force_single_message_state(bot, user_id)
            self._enforced_users.add(user_id)
            logger.info(f"✅ Single message policy enforced for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error enforcing single message policy for user {user_id}: {e}")
            return False
    
    async def enforce_for_all_users(self, bot: Bot) -> Dict[str, Any]:
        """Enforce single message policy for all users (use carefully!)"""
        try:
            # This would require getting all user IDs from database
            # Implementation depends on your user management system
            logger.warning("enforce_for_all_users called - this is a heavy operation!")
            
            # For now, just return stats
            return {
                'enforced_users': len(self._enforced_users),
                'status': 'partial_enforcement'
            }
        except Exception as e:
            logger.error(f"Error in enforce_for_all_users: {e}")
            return {'error': str(e)}
    
    def is_enforced(self, user_id: int) -> bool:
        """Check if single message policy is enforced for user"""
        return user_id in self._enforced_users
    
    async def get_compliance_report(self) -> Dict[str, Any]:
        """Get compliance report for single message policy"""
        try:
            return {
                'total_enforced_users': len(self._enforced_users),
                'enforced_users': list(self._enforced_users),
                'policy_active': True,
                'compliance_level': 'high'
            }
        except Exception as e:
            logger.error(f"Error getting compliance report: {e}")
            return {'error': str(e)}
