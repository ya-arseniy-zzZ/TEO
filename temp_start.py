    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command with universal single message system"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        # Initialize user in database
        db.create_or_update_user(
            user_id=user_id,
            username=update.effective_user.username,
            first_name=user_name
        )
        
        # Get weather settings from database
        weather_settings = db.get_weather_settings(user_id)
        if weather_settings and weather_settings.get('rain_alerts_enabled'):
            rain_monitor.enable_rain_alerts(user_id, weather_settings)
        
        # Delete the /start command first
        await update.message.delete()
        
        # Force clean state and send welcome message with universal system
        message = await self.message_manager.universal_send_message(
            bot=context.bot,
            user_id=user_id,
            text=MessageBuilder.welcome_message(user_name),
            reply_markup=KeyboardBuilder.main_menu(),
            parse_mode='Markdown'
        )
        
        # Enforce single message state for this user
        await self.single_message_state.enforce_for_user(context.bot, user_id)
        
        logger.info(f"✅ User {user_id} started bot with universal single message system")
