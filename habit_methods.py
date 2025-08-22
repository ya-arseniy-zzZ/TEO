"""
Additional habit tracking methods for Teo bot
These methods are separated to keep the main bot file manageable
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from habit_tracker import HabitTracker
from habit_interface import HabitInterface

# Import the global habit_tracker instance from teo_bot
# We'll pass it as parameter instead to avoid circular imports


async def show_habit_creation(query, user_id: int, habit_creation_data, user_states, habit_tracker):
    """Show habit creation options"""
    message = """➕ **Создание новой привычки**

Давай создадим привычку, которая поможет тебе стать лучше!

Выбери готовую привычку из списка или создай свою:"""
    
    keyboard, has_next = HabitInterface.create_habit_suggestions_keyboard(0)
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


async def show_habit_suggestions(query, user_id: int, page: int):
    """Show habit suggestions with pagination"""
    message = f"""💡 **Популярные привычки** (стр. {page + 1})

Выбери привычку из списка или создай свою:"""
    
    keyboard, has_next = HabitInterface.create_habit_suggestions_keyboard(page)
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


async def start_habit_creation_with_name(query, user_id: int, habit_name: str, habit_creation_data):
    """Start habit creation with a pre-selected name"""
    habit_creation_data[user_id] = {
        'name': habit_name,
        'description': '',
        'reminder_time': '09:00',
        'reminder_days': ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    }
    
    message = f"""✏️ **Настройка привычки: {habit_name}**

Хочешь добавить описание к этой привычке? Это поможет лучше мотивировать себя.

Отправь описание или нажми "Пропустить":"""
    
    keyboard = [
        [InlineKeyboardButton("⏭ Пропустить", callback_data='skip_description')],
        [InlineKeyboardButton("🔙 К выбору привычек", callback_data='create_habit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Set state for description input
    from teo_bot import user_states
    user_states[user_id] = 'waiting_habit_description'
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def show_custom_habit_input(query, user_id: int, user_states):
    """Show custom habit input instructions"""
    user_states[user_id] = 'waiting_habit_name'
    
    message = """✏️ **Создание своей привычки**

Напиши название привычки, которую хочешь отслеживать.

**Примеры:**
• `Выпить стакан воды`
• `Сделать зарядку`
• `Почитать 10 страниц`
• `Медитировать 5 минут`

Просто отправь сообщение с названием привычки."""
    
    keyboard = [
        [InlineKeyboardButton("🔙 К выбору привычек", callback_data='create_habit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def process_custom_habit_name(update, user_id: int, habit_name: str, habit_creation_data, user_states):
    """Process custom habit name input"""
    user_states.pop(user_id, None)
    
    habit_creation_data[user_id] = {
        'name': habit_name,
        'description': '',
        'reminder_time': '09:00',
        'reminder_days': ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    }
    
    message = f"""✏️ **Настройка привычки: {habit_name}**

Хочешь добавить описание к этой привычке?

Отправь описание или нажми "Пропустить":"""
    
    keyboard = [
        [InlineKeyboardButton("⏭ Пропустить", callback_data='skip_description')],
        [InlineKeyboardButton("🔙 К созданию привычки", callback_data='create_habit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_states[user_id] = 'waiting_habit_description'
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def process_habit_description(update, user_id: int, description: str, habit_creation_data, user_states):
    """Process habit description input"""
    user_states.pop(user_id, None)
    
    if user_id in habit_creation_data:
        habit_creation_data[user_id]['description'] = description
    
    await show_habit_time_selection(update, user_id, 0, habit_creation_data, is_message=True)


async def show_habit_time_selection(update_or_query, user_id: int, page: int, habit_creation_data, is_message=False):
    """Show time selection for habit"""
    habit_data = habit_creation_data.get(user_id, {})
    habit_name = habit_data.get('name', 'привычка')
    
    message = f"""⏰ **Время напоминания для "{habit_name}"**

Выбери время, когда тебе удобно получать напоминания:"""
    
    keyboard, has_next = HabitInterface.create_time_selection_keyboard(page)
    
    if is_message:
        await update_or_query.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update_or_query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


async def set_habit_time(query, user_id: int, time_str: str, habit_creation_data):
    """Set habit reminder time"""
    if user_id in habit_creation_data:
        habit_creation_data[user_id]['reminder_time'] = time_str
    
    await show_days_selection(query, user_id, habit_creation_data)


async def show_days_selection(query, user_id: int, habit_creation_data):
    """Show days selection for habit"""
    habit_data = habit_creation_data.get(user_id, {})
    habit_name = habit_data.get('name', 'привычка')
    selected_days = habit_data.get('reminder_days', [])
    
    message = f"""📅 **Дни напоминаний для "{habit_name}"**

Выбери дни, когда нужны напоминания:

Текущий выбор: {len(selected_days)}/7 дней"""
    
    keyboard = HabitInterface.create_days_selection_keyboard(selected_days)
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


async def toggle_habit_day(query, user_id: int, day: str, habit_creation_data):
    """Toggle a day for habit reminders"""
    if user_id not in habit_creation_data:
        return
    
    current_days = habit_creation_data[user_id].get('reminder_days', [])
    
    if day in current_days:
        current_days.remove(day)
    else:
        current_days.append(day)
    
    habit_creation_data[user_id]['reminder_days'] = current_days
    
    # Refresh the days selection
    await show_days_selection(query, user_id, habit_creation_data)


async def select_weekdays(query, user_id: int, habit_creation_data):
    """Select weekdays for habit"""
    if user_id not in habit_creation_data:
        return
    
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    habit_creation_data[user_id]['reminder_days'] = weekdays
    
    await show_days_selection(query, user_id, habit_creation_data)


async def select_all_days(query, user_id: int, habit_creation_data):
    """Select all days for habit"""
    if user_id not in habit_creation_data:
        return
    
    all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    habit_creation_data[user_id]['reminder_days'] = all_days
    
    await show_days_selection(query, user_id, habit_creation_data)


async def finalize_habit_creation(query, user_id: int, habit_creation_data, db):
    """Create the habit with collected data"""
    habit_data = habit_creation_data.get(user_id)
    
    if not habit_data:
        await query.edit_message_text(
            "❌ Ошибка создания привычки. Попробуй ещё раз.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
            ])
        )
        return
    
    # Generate habit ID
    import uuid
    habit_id = str(uuid.uuid4())[:8]
    
    # Get user's timezone settings
    weather_settings = db.get_weather_settings(user_id)
    user_timezone = weather_settings.get('timezone', 'Europe/Moscow') if weather_settings else 'Europe/Moscow'
    
    # Create the habit in database with timezone
    success = db.create_habit(
        habit_id=habit_id,
        user_id=user_id,
        name=habit_data['name'],
        description=habit_data.get('description', ''),
        reminder_time=habit_data.get('reminder_time', '09:00'),
        reminder_days=habit_data.get('reminder_days', []),
        timezone=user_timezone
    )
    
    # Clear creation data
    habit_creation_data.pop(user_id, None)
    
    message = f"""🎉 **Привычка создана!**

✅ **{habit_data['name']}** успешно добавлена в твой список!

⏰ Напоминания: {habit_data.get('reminder_time', '09:00')}
📅 Дни: {len(habit_data.get('reminder_days', []))}/7

Начни формировать полезную привычку уже сегодня! 💪"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Мои привычки", callback_data='view_habits')],
        [InlineKeyboardButton("🎯 К привычкам", callback_data='habits_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def show_habit_management(query, user_id: int, page: int, db):
    """Show habit management interface"""
    habits = db.get_user_habits(user_id)
    
    if not habits:
        message = """⚙️ **Управление привычками**

У тебя пока нет привычек для управления."""
        
        keyboard = [
            [InlineKeyboardButton("➕ Создать привычку", callback_data='create_habit')],
            [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        total_pages = HabitInterface.get_page_count(len(habits))
        message = f"""⚙️ **Управление привычками** (стр. {page + 1}/{total_pages})

Выбери привычку для редактирования или удаления:"""
        
        keyboard, has_next = HabitInterface.create_management_keyboard(habits, page)
        reply_markup = keyboard
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def confirm_delete_habit(query, user_id: int, habit_id: str, db):
    """Show delete confirmation"""
    habit = db.get_habit(habit_id)
    
    if not habit or habit['user_id'] != user_id:
        await query.edit_message_text(
            "❌ Привычка не найдена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
            ])
        )
        return
    
    message = f"""🗑 **Удаление привычки**

Ты уверен, что хочешь удалить привычку:
**{habit['name']}**?

Это действие нельзя отменить."""
    
    keyboard = HabitInterface.create_confirmation_keyboard('delete', habit_id)
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


async def delete_habit(query, user_id: int, habit_id: str, db):
    """Delete a habit"""
    habit = db.get_habit(habit_id)
    
    if habit and habit['user_id'] == user_id:
        habit_name = habit['name']
        success = db.delete_habit(habit_id)
        
        if success:
            message = f"✅ Привычка **{habit_name}** удалена."
        else:
            message = "❌ Не удалось удалить привычку."
    else:
        message = "❌ Привычка не найдена."
    
    keyboard = [
        [InlineKeyboardButton("📋 Мои привычки", callback_data='view_habits')],
        [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def edit_habit(query, user_id: int, habit_id: str):
    """Edit habit (placeholder for now)"""
    message = """✏️ **Редактирование привычки**

Функция редактирования будет добавлена в следующем обновлении.

Пока что ты можешь удалить привычку и создать новую."""
    
    keyboard = [
        [InlineKeyboardButton(f"🗑 Удалить", callback_data=f'delete_habit_{habit_id}')],
        [InlineKeyboardButton("🔙 К деталям", callback_data=f'habit_details_{habit_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def show_habit_time_selection(query, user_id: int, page: int, habit_creation_data):
    """Show habit time selection with pagination"""
    message = f"""⏰ **Выбор времени напоминаний** (стр. {page + 1})

Выбери время для напоминаний о привычке:"""
    
    keyboard, has_next = HabitInterface.create_habit_time_keyboard(page)
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


async def set_habit_time(query, user_id: int, time_str: str, habit_creation_data):
    """Set habit reminder time"""
    if user_id in habit_creation_data:
        habit_creation_data[user_id]['reminder_time'] = time_str
        
        message = f"""✅ **Время напоминаний установлено: {time_str}**

Теперь выбери дни недели для напоминаний:"""
        
        keyboard = HabitInterface.create_days_selection_keyboard()
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    else:
        # If no habit creation data, go back to habit creation
        await query.edit_message_text(
            "❌ Ошибка. Попробуй создать привычку заново.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
            ])
        )


async def show_custom_habit_time_input(query, user_id: int, habit_creation_data):
    """Show custom habit time input instructions"""
    from teo_bot import user_states
    user_states[user_id] = 'waiting_habit_time_input'
    
    message = """✏️ **Ввод своего времени**

Напиши время в формате ЧЧ:ММ для напоминаний о привычке.

**Примеры:**
• `07:30`
• `08:00`
• `21:15`

Просто отправь сообщение с временем."""
    
    keyboard = HabitInterface.create_custom_habit_time_keyboard()
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


async def process_custom_habit_time(update, user_id: int, time_str: str, habit_creation_data, user_states):
    """Process custom habit time input"""
    user_states.pop(user_id, None)
    
    try:
        from datetime import datetime
        datetime.strptime(time_str, '%H:%M')  # Validate time format
        
        if user_id in habit_creation_data:
            habit_creation_data[user_id]['reminder_time'] = time_str
            
            message = f"""✅ **Время напоминаний установлено: {time_str}**

Теперь выбери дни недели для напоминаний:"""
            
            keyboard = HabitInterface.create_days_selection_keyboard()
            await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Ошибка. Попробуй создать привычку заново.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К привычкам", callback_data='habits_menu')]
                ])
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат времени. Используй формат ЧЧ:ММ (например, 08:00).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К выбору времени", callback_data='habit_time_page_0')]
            ])
        )
