"""
Message Manager for Teo Bot
Handles automatic deletion of previous bot messages to keep chat clean
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any
from telegram import Bot, Message
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class MessageManager:
    """Manages bot messages with automatic cleanup"""
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.max_messages_per_user = 5  # Keep only last 5 messages per user
    
    async def send_message_with_cleanup(
        self, 
        bot: Bot, 
        user_id: int, 
        text: str, 
        **kwargs
    ) -> Optional[Message]:
        """
        Send message and automatically delete previous bot messages
        """
        try:
            # Delete previous bot messages
            await self._delete_previous_messages(bot, user_id)
            
            # Send new message
            message = await bot.send_message(chat_id=user_id, text=text, **kwargs)
            
            # Save message to history
            if message:
                self.db.save_bot_message(
                    user_id=user_id,
                    message_id=message.message_id,
                    chat_id=message.chat_id,
                    message_type='text'
                )
            
            return message
            
        except Exception as e:
            logger.error(f"Error sending message with cleanup for user {user_id}: {e}")
            return None
    
    async def edit_message_with_cleanup(
        self, 
        bot: Bot, 
        user_id: int, 
        message_id: int, 
        text: str, 
        **kwargs
    ) -> Optional[Message]:
        """
        Edit message and automatically delete other bot messages
        """
        try:
            # Delete other bot messages (except the one being edited)
            await self._delete_other_messages(bot, user_id, message_id)
            
            # Edit the message
            message = await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=text,
                **kwargs
            )
            
            # Update message in history
            if message:
                self.db.save_bot_message(
                    user_id=user_id,
                    message_id=message.message_id,
                    chat_id=message.chat_id,
                    message_type='text'
                )
            
            return message
            
        except Exception as e:
            logger.error(f"Error editing message with cleanup for user {user_id}: {e}")
            return None
    
    async def send_media_with_cleanup(
        self, 
        bot: Bot, 
        user_id: int, 
        media_type: str, 
        media_data: Any, 
        **kwargs
    ) -> Optional[Message]:
        """
        Send media message and automatically delete previous bot messages
        """
        try:
            # Delete previous bot messages
            await self._delete_previous_messages(bot, user_id)
            
            # Send media message
            if media_type == 'photo':
                message = await bot.send_photo(chat_id=user_id, photo=media_data, **kwargs)
            elif media_type == 'document':
                message = await bot.send_document(chat_id=user_id, document=media_data, **kwargs)
            elif media_type == 'video':
                message = await bot.send_video(chat_id=user_id, video=media_data, **kwargs)
            else:
                logger.error(f"Unsupported media type: {media_type}")
                return None
            
            # Save message to history
            if message:
                self.db.save_bot_message(
                    user_id=user_id,
                    message_id=message.message_id,
                    chat_id=message.chat_id,
                    message_type=media_type
                )
            
            return message
            
        except Exception as e:
            logger.error(f"Error sending media with cleanup for user {user_id}: {e}")
            return None
    
    async def _delete_previous_messages(self, bot: Bot, user_id: int) -> None:
        """Delete previous bot messages for user"""
        try:
            # Get user's bot messages history
            messages = self.db.get_user_bot_messages(user_id, limit=self.max_messages_per_user)
            
            # Delete messages
            for msg_data in messages:
                await self._delete_message_safe(bot, user_id, msg_data['message_id'])
                self.db.delete_bot_message(user_id, msg_data['message_id'])
                
        except Exception as e:
            logger.error(f"Error deleting previous messages for user {user_id}: {e}")
    
    async def _delete_other_messages(self, bot: Bot, user_id: int, keep_message_id: int) -> None:
        """Delete other bot messages except the specified one"""
        try:
            # Get user's bot messages history
            messages = self.db.get_user_bot_messages(user_id, limit=self.max_messages_per_user)
            
            # Delete messages except the one being kept
            for msg_data in messages:
                if msg_data['message_id'] != keep_message_id:
                    await self._delete_message_safe(bot, user_id, msg_data['message_id'])
                    self.db.delete_bot_message(user_id, msg_data['message_id'])
                    
        except Exception as e:
            logger.error(f"Error deleting other messages for user {user_id}: {e}")
    
    async def _delete_message_safe(self, bot: Bot, user_id: int, message_id: int) -> bool:
        """Safely delete a message with error handling"""
        try:
            await bot.delete_message(chat_id=user_id, message_id=message_id)
            return True
        except TelegramError as e:
            if "message to delete not found" in str(e).lower():
                # Message already deleted, remove from database
                self.db.delete_bot_message(user_id, message_id)
                return True
            else:
                logger.warning(f"Could not delete message {message_id} for user {user_id}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error deleting message {message_id} for user {user_id}: {e}")
            return False
    
    async def clear_user_messages(self, bot: Bot, user_id: int) -> bool:
        """Clear all bot messages for user"""
        try:
            # Get all user's bot messages
            messages = self.db.get_user_bot_messages(user_id, limit=100)
            
            # Delete all messages
            for msg_data in messages:
                await self._delete_message_safe(bot, user_id, msg_data['message_id'])
            
            # Clear from database
            self.db.clear_user_bot_messages(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing messages for user {user_id}: {e}")
            return False
    
    def get_user_message_count(self, user_id: int) -> int:
        """Get count of bot messages for user"""
        try:
            messages = self.db.get_user_bot_messages(user_id, limit=1000)
            return len(messages)
        except Exception as e:
            logger.error(f"Error getting message count for user {user_id}: {e}")
            return 0
