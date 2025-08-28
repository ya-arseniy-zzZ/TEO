# 🎯 Universal Single Message System

## Обзор

Универсальная система одного сообщения гарантирует, что в чате с пользователем всегда находится только одно сообщение от бота. Эта система автоматически применяется ко всем функциям бота.

## 🚀 Быстрый старт для разработчиков

### Для новых функций - ВСЕГДА используйте:

```python
# ✅ ПРАВИЛЬНО - Отправка сообщения
await self.send_universal_message(
    bot=context.bot,
    user_id=user_id,
    text="Ваше сообщение",
    reply_markup=keyboard,
    parse_mode='Markdown'
)

# ✅ ПРАВИЛЬНО - Редактирование сообщения
await self.edit_universal_message(
    bot=context.bot,
    user_id=user_id,
    text="Обновленное сообщение",
    reply_markup=new_keyboard
)

# ✅ ПРАВИЛЬНО - Отправка медиа
await self.send_universal_message(
    bot=context.bot,
    user_id=user_id,
    text="Подпись к фото",
    media_type='photo',
    media_data=photo_file,
    reply_markup=keyboard
)
```

### ❌ НЕ используйте напрямую:

```python
# ❌ НЕПРАВИЛЬНО
await context.bot.send_message(...)
await context.bot.send_photo(...)
await update.message.reply_text(...)
```

## 📚 Основные компоненты

### 1. MessageManager
Основной класс для управления сообщениями:

```python
# Универсальная отправка
await message_manager.universal_send_message(bot, user_id, text, **kwargs)

# Универсальное редактирование
await message_manager.universal_edit_message(bot, user_id, message_id, text, **kwargs)

# Принудительная очистка
await message_manager.force_single_message_state(bot, user_id)
```

### 2. SingleMessageDecorator
Декораторы для автоматического применения политики:

```python
@with_single_message_policy(message_manager)
async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Автоматическая очистка применяется
    pass

@self.single_message_decorator.ensure_single_message()
async def my_function(update, context):
    # Функция с автоматической очисткой
    pass
```

### 3. SingleMessageState
Управление состоянием системы:

```python
# Принудительное применение для пользователя
await single_message_state.enforce_for_user(bot, user_id)

# Проверка применения
if single_message_state.is_enforced(user_id):
    print("Политика активна")

# Отчет о соответствии
report = await single_message_state.get_compliance_report()
```

## 🔧 Интеграция в TeoBot

### Методы TeoBot для разработчиков:

```python
# В любом методе TeoBot используйте:
class TeoBot:
    async def my_new_feature(self, update, context):
        user_id = update.effective_user.id
        
        # Отправка сообщения
        await self.send_universal_message(
            bot=context.bot,
            user_id=user_id,
            text="Новая функция работает!",
            reply_markup=some_keyboard
        )
        
        # Или редактирование
        await self.edit_universal_message(
            bot=context.bot,
            user_id=user_id,
            text="Обновлено!"
        )
```

## 📋 Типы поддерживаемых сообщений

### Текстовые сообщения:
```python
await self.send_universal_message(
    bot=context.bot,
    user_id=user_id,
    text="Текст сообщения",
    parse_mode='Markdown',
    reply_markup=keyboard
)
```

### Медиа сообщения:
```python
# Фото
await self.send_universal_message(
    bot=context.bot,
    user_id=user_id,
    media_type='photo',
    media_data=photo_file,
    caption="Подпись к фото"
)

# Документ
await self.send_universal_message(
    bot=context.bot,
    user_id=user_id,
    media_type='document',
    media_data=document_file,
    caption="Описание документа"
)

# Видео
await self.send_universal_message(
    bot=context.bot,
    user_id=user_id,
    media_type='video',
    media_data=video_file,
    caption="Описание видео"
)

# Поддерживаются: photo, document, video, animation, sticker, voice, audio
```

## 🛠 Продвинутые возможности

### Принудительная очистка:
```python
# Очистить все сообщения пользователя
await self.message_manager.force_single_message_state(context.bot, user_id)

# Гарантированная очистка с сохранением определенного сообщения
await self.message_manager._guarantee_single_message_cleanup(
    context.bot, user_id, keep_message_id=some_id
)
```

### Статистика и мониторинг:
```python
# Статистика пользователя
stats = self.message_manager.get_single_message_stats(user_id)

# Отчет о соответствии
report = self.get_single_message_compliance_report()

# Количество сообщений
count = self.message_manager.get_user_message_count(user_id)
```

## 🎯 Лучшие практики

### 1. Всегда используйте универсальные методы
```python
# ✅ ПРАВИЛЬНО
await self.send_universal_message(bot, user_id, text)

# ❌ НЕПРАВИЛЬНО  
await bot.send_message(user_id, text)
```

### 2. Для callback handlers:
```python
async def button_handler(self, update, context):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Отвечаем на callback
    await query.answer()
    
    # Используем универсальное редактирование
    await self.edit_universal_message(
        bot=context.bot,
        user_id=user_id,
        message_id=query.message.message_id,
        text="Новый контент",
        reply_markup=new_keyboard
    )
```

### 3. Для обработки ошибок:
```python
try:
    await self.send_universal_message(bot, user_id, text)
except Exception as e:
    logger.error(f"Error in universal message: {e}")
    # Fallback - принудительная очистка
    await self.message_manager.force_single_message_state(bot, user_id)
```

### 4. При добавлении новых функций:
```python
async def new_feature_handler(self, update, context):
    """Новая функция - ОБЯЗАТЕЛЬНО с декоратором"""
    user_id = update.effective_user.id
    
    # Автоматически применяем систему
    await self.single_message_state.enforce_for_user(context.bot, user_id)
    
    # Ваша логика
    result = calculate_something()
    
    # Отправляем результат
    await self.send_universal_message(
        bot=context.bot,
        user_id=user_id,
        text=f"Результат: {result}",
        reply_markup=result_keyboard
    )
```

## 🔍 Отладка и тестирование

### Проверка состояния системы:
```python
# В любом методе можете проверить
stats = self.message_manager.get_single_message_stats(user_id)
print(f"Сообщений у пользователя: {stats['total_messages_tracked']}")
print(f"Соответствие: {stats['compliance']}")

# Принудительная проверка
if stats['total_messages_tracked'] > 1:
    logger.warning(f"⚠️ User {user_id} has multiple messages!")
    await self.message_manager.force_single_message_state(context.bot, user_id)
```

### Логирование:
Система автоматически логирует все операции:
- `✅ Single message sent to user X`
- `🧹 Cleanup for user X: deleted Y, kept Z`
- `🎯 Applying single message policy for user X`

## 📈 Мониторинг

### Отчеты системы:
```python
# Общий отчет
report = self.get_single_message_compliance_report()

# Отчет по пользователю
user_report = await self.single_message_state.get_compliance_report()
```

## ⚡ Быстрые команды для разработки

```bash
# Поиск использования старых методов (которые нужно заменить)
grep -r "send_message\|reply_text\|send_photo" app/

# Поиск универсальных методов (правильное использование)
grep -r "universal_send_message\|universal_edit_message" app/
```

## 🚨 Важные замечания

1. **Всегда используйте универсальные методы** для новых функций
2. **Не обходите систему** - это нарушит целостность
3. **Тестируйте на чистом чате** - проверяйте, что остается только одно сообщение
4. **Логируйте ошибки** - система должна работать без сбоев
5. **Для существующих функций** - постепенно переводите на универсальные методы

## 📞 Поддержка

При возникновении проблем с системой:
1. Проверьте логи (`🧹 Cleanup`, `✅ Single message`)
2. Используйте `force_single_message_state` для сброса
3. Проверьте отчет соответствия
4. Убедитесь в использовании универсальных методов

