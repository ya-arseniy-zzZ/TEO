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

    # ===============================
    # UNIVERSAL SINGLE MESSAGE SYSTEM
    # ===============================
    
    async def universal_send_message(
        self, 
        bot: Bot, 
        user_id: int, 
        text: str = None,
        media_type: str = None,
        media_data: Any = None,
        **kwargs
    ) -> Optional[Message]:
        """
        Universal method for sending ANY type of message with guaranteed single message cleanup
        This method ensures only ONE bot message exists at any time
        """
        try:
            # Step 1: Always clean ALL previous bot messages first
            await self._guarantee_single_message_cleanup(bot, user_id)
            
            # Step 2: Send the new message based on type
            message = None
            
            if media_type and media_data:
                # Send media message
                if media_type == 'photo':
                    message = await bot.send_photo(chat_id=user_id, photo=media_data, **kwargs)
                elif media_type == 'document':
                    message = await bot.send_document(chat_id=user_id, document=media_data, **kwargs)
                elif media_type == 'video':
                    message = await bot.send_video(chat_id=user_id, video=media_data, **kwargs)
                elif media_type == 'animation':
                    message = await bot.send_animation(chat_id=user_id, animation=media_data, **kwargs)
                elif media_type == 'sticker':
                    message = await bot.send_sticker(chat_id=user_id, sticker=media_data, **kwargs)
                elif media_type == 'voice':
                    message = await bot.send_voice(chat_id=user_id, voice=media_data, **kwargs)
                elif media_type == 'audio':
                    message = await bot.send_audio(chat_id=user_id, audio=media_data, **kwargs)
                else:
                    logger.error(f"Unsupported media type: {media_type}")
                    return None
                    
                # Save media message to history
                if message:
                    self.db.save_bot_message(
                        user_id=user_id,
                        message_id=message.message_id,
                        chat_id=message.chat_id,
                        message_type=media_type
                    )
            elif text:
                # Send text message
                message = await bot.send_message(chat_id=user_id, text=text, **kwargs)
                
                # Save text message to history
                if message:
                    self.db.save_bot_message(
                        user_id=user_id,
                        message_id=message.message_id,
                        chat_id=message.chat_id,
                        message_type='text'
                    )
            else:
                logger.error("Either text or media must be provided")
                return None
            
            # Step 3: Update main message ID for the user
            if message:
                self.db.save_user_main_message(user_id, message.message_id)
                logger.info(f"✅ Single message sent to user {user_id}, message_id: {message.message_id}")
            
            return message
            
        except Exception as e:
            logger.error(f"Error in universal_send_message for user {user_id}: {e}")
            return None
    
    async def universal_edit_message(
        self, 
        bot: Bot, 
        user_id: int, 
        message_id: int = None,
        text: str = None,
        media_type: str = None,
        media_data: Any = None,
        **kwargs
    ) -> Optional[Message]:
        """
        Universal method for editing messages with guaranteed single message cleanup
        """
        try:
            # Get current main message ID if not provided
            if not message_id:
                message_id = self.db.get_user_main_message_id(user_id)
                if not message_id:
                    # No existing message to edit, send new one
                    return await self.universal_send_message(bot, user_id, text, media_type, media_data, **kwargs)
            
            # Clean other messages except the one being edited
            await self._guarantee_single_message_cleanup(bot, user_id, keep_message_id=message_id)
            
            # Edit the message
            message = None
            
            if media_type and media_data:
                # Edit media message
                try:
                    from telegram import InputMediaPhoto, InputMediaDocument, InputMediaVideo
                    
                    if media_type == 'photo':
                        media = InputMediaPhoto(media=media_data, caption=kwargs.get('caption', ''))
                        message = await bot.edit_message_media(
                            chat_id=user_id,
                            message_id=message_id,
                            media=media,
                            reply_markup=kwargs.get('reply_markup')
                        )
                    elif media_type == 'document':
                        media = InputMediaDocument(media=media_data, caption=kwargs.get('caption', ''))
                        message = await bot.edit_message_media(
                            chat_id=user_id,
                            message_id=message_id,
                            media=media,
                            reply_markup=kwargs.get('reply_markup')
                        )
                    elif media_type == 'video':
                        media = InputMediaVideo(media=media_data, caption=kwargs.get('caption', ''))
                        message = await bot.edit_message_media(
                            chat_id=user_id,
                            message_id=message_id,
                            media=media,
                            reply_markup=kwargs.get('reply_markup')
                        )
                    else:
                        logger.error(f"Unsupported media type for editing: {media_type}")
                        return None
                except Exception as edit_error:
                    logger.warning(f"Failed to edit media message: {edit_error}, sending new message instead")
                    return await self.universal_send_message(bot, user_id, text, media_type, media_data, **kwargs)
                    
            elif text:
                # Edit text message
                try:
                    message = await bot.edit_message_text(
                        chat_id=user_id,
                        message_id=message_id,
                        text=text,
                        **kwargs
                    )
                except Exception as edit_error:
                    logger.warning(f"Failed to edit text message: {edit_error}, sending new message instead")
                    return await self.universal_send_message(bot, user_id, text, media_type, media_data, **kwargs)
            else:
                logger.error("Either text or media must be provided for editing")
                return None
            
            # Update message in history
            if message:
                self.db.save_bot_message(
                    user_id=user_id,
                    message_id=message.message_id,
                    chat_id=message.chat_id,
                    message_type=media_type if media_type else 'text'
                )
                logger.info(f"✅ Single message edited for user {user_id}, message_id: {message.message_id}")
            
            return message
            
        except Exception as e:
            logger.error(f"Error in universal_edit_message for user {user_id}: {e}")
            # Fallback to sending new message
            return await self.universal_send_message(bot, user_id, text, media_type, media_data, **kwargs)
    
    async def _guarantee_single_message_cleanup(
        self, 
        bot: Bot, 
        user_id: int, 
        keep_message_id: int = None
    ) -> None:
        """
        GUARANTEED cleanup - ensures only one message remains
        This is the core method that enforces single message rule
        """
        try:
            # Get ALL bot messages for this user
            messages = self.db.get_user_bot_messages(user_id, limit=100)  # Get more messages to be sure
            
            deleted_count = 0
            kept_count = 0
            
            for msg_data in messages:
                message_id = msg_data.get('message_id')
                
                if message_id and message_id != keep_message_id:
                    # Delete this message
                    success = await self._delete_message_safe(bot, user_id, message_id)
                    if success:
                        self.db.delete_bot_message(user_id, message_id)
                        deleted_count += 1
                elif message_id == keep_message_id:
                    kept_count += 1
            
            logger.info(f"🧹 Cleanup for user {user_id}: deleted {deleted_count}, kept {kept_count}")
            
        except Exception as e:
            logger.error(f"Error in _guarantee_single_message_cleanup for user {user_id}: {e}")
    
    async def force_single_message_state(self, bot: Bot, user_id: int) -> bool:
        """
        Force single message state - emergency cleanup method
        Use this to ensure clean state before important operations
        """
        try:
            logger.info(f"🚨 Forcing single message state for user {user_id}")
            
            # Clear ALL bot messages
            await self.clear_user_messages(bot, user_id)
            
            # Clear main message ID
            self.db.save_user_main_message(user_id, None)
            
            logger.info(f"✅ Single message state enforced for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error forcing single message state for user {user_id}: {e}")
            return False
    
    def enable_single_message_mode(self, user_id: int) -> bool:
        """
        Enable single message mode for user (future feature)
        """
        try:
            # This could be stored in user settings in database
            # For now, it's always enabled
            logger.info(f"Single message mode enabled for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error enabling single message mode for user {user_id}: {e}")
            return False
    
    def get_single_message_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get statistics about single message system for user
        """
        try:
            messages = self.db.get_user_bot_messages(user_id, limit=100)
            main_message_id = self.db.get_user_main_message_id(user_id)
            
            return {
                'total_messages_tracked': len(messages),
                'main_message_id': main_message_id,
                'single_message_mode_active': True,
                'last_cleanup': 'automatic',
                'compliance': len(messages) <= 1  # Should always be True
            }
        except Exception as e:
            logger.error(f"Error getting single message stats for user {user_id}: {e}")
            return {'error': str(e)}

