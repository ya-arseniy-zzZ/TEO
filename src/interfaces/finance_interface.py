"""
Finance interface for Teo bot
Provides user interface for Google Sheets financial data analysis
"""
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.services.finance_service import finance_service
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)
db = DatabaseManager()


class FinanceInterface:
    """Handles finance-related bot interactions"""
    
    @staticmethod
    def create_navigation_keyboard(back_callback: str, include_main_menu: bool = True) -> InlineKeyboardMarkup:
        """Create standard navigation keyboard with back and main menu buttons"""
        keyboard = []
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=back_callback)])
        
        # Add main menu button if requested
        if include_main_menu:
            keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    async def _edit_message_safely(query, text, reply_markup=None):
        """Safely edit message, handling both text and photo messages"""
        if query.message.photo:
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @staticmethod
    def create_finance_menu() -> InlineKeyboardMarkup:
        """Create main finance menu"""
        keyboard = [
            [InlineKeyboardButton("📊 Анализ за месяц", callback_data='finance_month')],
            [InlineKeyboardButton("📈 Анализ за неделю", callback_data='finance_week')],
            [InlineKeyboardButton("📅 Анализ за день", callback_data='finance_day')],
            [InlineKeyboardButton("💰 Общий анализ", callback_data='finance_all')],
            [InlineKeyboardButton("⚙️ Настройки таблицы", callback_data='finance_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_settings_menu() -> InlineKeyboardMarkup:
        """Create finance settings menu"""
        keyboard = [
            [InlineKeyboardButton("📝 Указать ссылку на таблицу", callback_data='finance_set_url')],
            [InlineKeyboardButton("🔗 Показать текущую ссылку", callback_data='finance_show_url')],
            [InlineKeyboardButton("❌ Удалить настройки", callback_data='finance_clear_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_period_menu() -> InlineKeyboardMarkup:
        """Create period selection menu"""
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data='finance_period_day')],
            [InlineKeyboardButton("📊 Неделя", callback_data='finance_period_week')],
            [InlineKeyboardButton("📈 Месяц", callback_data='finance_period_month')],
            [InlineKeyboardButton("📊 Год", callback_data='finance_period_year')],
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    async def handle_finance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle finance menu selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Check if user has configured Google Sheets
        finance_settings = db.get_finance_settings(user_id)
        if not finance_settings:
            await FinanceInterface._edit_message_safely(
                query,
                "💰 *Финансовый анализ*\n\n"
                "Здесь мы проанализируем твои расходы и доходы из Google Таблицы: динамика, категории, бюджеты, предиктивные инсайты.\n\n"
                "📋 *Подключи таблицу в 2 шага:*\n"
                "1. Дай ссылку на таблицу\n"
                "2. Выбери лист с данными\n\n"
                "🎯 *Что ты получишь:*\n"
                "• Анализ доходов и расходов\n"
                "• Группировка по категориям\n"
                "• Динамика за периоды\n"
                "• Предиктивные инсайты",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Подключить таблицу", callback_data='finance_connect')],
                    [InlineKeyboardButton("📋 Требования к формату", callback_data='finance_format_requirements')],
                    [InlineKeyboardButton("🎮 Демо-режим", callback_data='finance_demo')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
                ])
            )
            return 'finance_menu'
        
        # Show financial dashboard for connected users
        await FinanceInterface._show_financial_dashboard(update, context)
        return 'finance_menu'
    
    @staticmethod
    async def _show_financial_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show financial dashboard with current month summary"""
        query = update.callback_query
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        # Show loading message
        await FinanceInterface._edit_message_safely(
            query,
            "⏳ Загружаю финансовые данные...",
            reply_markup=FinanceInterface.create_navigation_keyboard('main_menu', include_main_menu=False)
        )
        
        try:
            # Get current month analysis
            sheet_id = finance_service.extract_sheet_id_from_url(finance_settings['url'])
            raw_data = finance_service.get_sheet_data(sheet_id, finance_settings['sheet_name'])
            parsed_data = finance_service.parse_financial_data(raw_data)
            current_month_analysis = finance_service.analyze_finances(parsed_data, 'month')
            
            # Get week trend
            week_analysis = finance_service.analyze_finances(parsed_data, 'week')
            previous_week_analysis = finance_service.get_previous_period_analysis(parsed_data, 'week')
            
            # Calculate week trend percentage
            week_trend = 0
            if previous_week_analysis['total_expenses'] > 0:
                week_trend = ((week_analysis['total_expenses'] - previous_week_analysis['total_expenses']) / 
                             previous_week_analysis['total_expenses']) * 100
            
            # Format dashboard message
            message = "💰 *Финансовый дайджест*\n\n"
            
            # Monthly summary
            message += f"📊 *Итоги за месяц:*\n"
            message += f"• Расходы: {current_month_analysis['total_expenses']:,.0f} ₽\n"
            message += f"• Доходы: {current_month_analysis['total_income']:,.0f} ₽\n"
            message += f"• Баланс: {current_month_analysis['balance']:,.0f} ₽\n\n"
            
            # Top expense categories
            if current_month_analysis['expense_categories']:
                message += "📉 *Топ-3 категории расходов:*\n"
                for i, (category, amount) in enumerate(list(current_month_analysis['expense_categories'].items())[:3], 1):
                    message += f"{i}. {category}: {amount:,.0f} ₽\n"
                message += "\n"
            
            # Week trend
            trend_icon = "↓" if week_trend < 0 else "↑"
            message += f"📈 *Тренд недели:* расходы {trend_icon} {abs(week_trend):.1f}% vs прошлая неделя\n\n"
            
            # Quick insights
            message += "💡 *Быстрые действия:*\n"
            message += "• Нажмите 'Аналитика за месяц' для деталей\n"
            message += "• 'По категориям' покажет куда уходят деньги\n"
            message += "• 'Тренды и прогноз' для планирования"
            
            # Dashboard keyboard
            keyboard = [
                [InlineKeyboardButton("📊 Аналитика за месяц", callback_data='finance_monthly_analytics')],
                [InlineKeyboardButton("📋 По категориям", callback_data='finance_categories')],
                [InlineKeyboardButton("📈 Тренды и прогноз", callback_data='finance_trends')],
                [InlineKeyboardButton("💰 Бюджеты и лимиты", callback_data='finance_budgets')],
                [InlineKeyboardButton("🔍 Поиск по операциям", callback_data='finance_search')],
                [InlineKeyboardButton("🔄 Обновить данные", callback_data='finance_refresh')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='finance_settings')],
                [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            await FinanceInterface._edit_message_safely(
                query,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing financial dashboard for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(
                query,
                "❌ Ошибка при загрузке финансовых данных.\n\n"
                "Попробуйте обновить данные или проверьте настройки таблицы.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Обновить данные", callback_data='finance_refresh')],
                    [InlineKeyboardButton("⚙️ Настройки", callback_data='finance_settings')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ])
            )
    
    @staticmethod
    async def handle_finance_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle finance settings menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        if finance_settings:
            status_text = "✅ Таблица настроена"
        else:
            status_text = "❌ Таблица не настроена"
        
        await FinanceInterface._edit_message_safely(
            query,
            f"⚙️ *Настройки финансов*\n\n"
            f"Статус: {status_text}\n\n"
            f"Выберите действие:",
            reply_markup=FinanceInterface.create_settings_menu()
        )
        return 'finance_settings'
    
    @staticmethod
    async def handle_set_sheet_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle setting Google Sheets URL"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Set user state to wait for URL
        context.user_data['waiting_for'] = 'waiting_for_finance_sheet_url'
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            await query.edit_message_caption(
                caption="📝 *Настройка Google Sheets*\n\n"
                "Отправьте ссылку на вашу Google таблицу.\n\n"
                "📋 *Как получить ссылку:*\n"
                "1. Откройте вашу Google таблицу\n"
                "2. Нажмите 'Настройки доступа' (справа вверху)\n"
                "3. Выберите 'Доступно всем, у кого есть ссылка'\n"
                "4. Скопируйте ссылку из адресной строки\n\n"
                "📊 *Структура таблицы должна содержать:*\n"
                "• Дата (формат: ДД.ММ.ГГГГ)\n"
                "• Сумма (число)\n"
                "• Тип (Доход/Расход)\n"
                "• Основная категория\n\n"
                "⚠️ *Важно:* Таблица должна быть доступна для просмотра всем, у кого есть ссылка.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data='finance_settings')]
                ]),
                parse_mode='Markdown'
            )
        else:
            await FinanceInterface._edit_message_safely(
                query,
                "📝 *Настройка Google Sheets*\n\n"
                "Отправьте ссылку на вашу Google таблицу.\n\n"
                "📋 *Как получить ссылку:*\n"
                "1. Откройте вашу Google таблицу\n"
                "2. Нажмите 'Настройки доступа' (справа вверху)\n"
                "3. Выберите 'Доступно всем, у кого есть ссылка'\n"
                "4. Скопируйте ссылку из адресной строки\n\n"
                "📊 *Структура таблицы должна содержать:*\n"
                "• Дата (формат: ДД.ММ.ГГГГ)\n"
                "• Сумма (число)\n"
                "• Тип (Доход/Расход)\n"
                "• Основная категория\n\n"
                "⚠️ *Важно:* Таблица должна быть доступна для просмотра всем, у кого есть ссылка.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data='finance_settings')]
                ])
            )
        return 'waiting_for_url'
    
    @staticmethod
    async def handle_connect_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle table connection initiation"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Set user state to wait for URL
        context.user_data['waiting_for'] = 'waiting_for_finance_sheet_url'
        
        await FinanceInterface._edit_message_safely(
            query,
            "🔗 *Подключение Google Таблицы*\n\n"
            "Отправьте ссылку на вашу Google таблицу.\n\n"
            "📋 *Как получить ссылку:*\n"
            "1. Откройте вашу Google таблицу\n"
            "2. Нажмите 'Настройки доступа' (справа вверху)\n"
            "3. Выберите 'Доступно всем, у кого есть ссылка'\n"
            "4. Скопируйте ссылку из адресной строки\n\n"
            "⚠️ *Важно:* Таблица должна быть доступна для просмотра всем, у кого есть ссылка.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data='finance_menu')]
            ])
        )
        return 'waiting_for_url'
    
    @staticmethod
    async def handle_format_requirements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle format requirements display"""
        query = update.callback_query
        await query.answer()
        
        await FinanceInterface._edit_message_safely(
            query,
            "📋 *Требования к формату таблицы*\n\n"
            "Ваша таблица должна содержать следующие столбцы:\n\n"
            "📅 **Дата** - дата операции (формат: ДД.ММ.ГГГГ)\n"
            "💰 **Сумма** - числовое значение\n"
            "📊 **Тип** - Доход/Расход или +/-\n"
            "🏷️ **Категория** - основная категория\n"
            "💬 **Комментарий** - описание операции (опционально)\n\n"
            "📝 *Пример строки:*\n"
            "`25.08.2025 | 1000 | Доход | Зарплата | Аванс`\n"
            "`25.08.2025 | -500 | Расход | Продукты | Пятёрочка`\n\n"
            "✅ *Поддерживаемые форматы:*\n"
            "• Тип: Доход/Расход, Income/Expense, +/-, 1/-1\n"
            "• Дата: ДД.ММ.ГГГГ, ГГГГ-ММ-ДД, ДД/ММ/ГГГГ",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Показать пример шаблона", callback_data='finance_show_template')],
                [InlineKeyboardButton("🔗 Подключить таблицу", callback_data='finance_connect')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
            ])
        )
        return 'format_requirements'
    
    @staticmethod
    async def handle_show_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle template example display"""
        query = update.callback_query
        await query.answer()
        
        await FinanceInterface._edit_message_safely(
            query,
            "📄 *Пример шаблона таблицы*\n\n"
            "Создайте таблицу с такой структурой:\n\n"
            "| Дата | Сумма | Тип | Категория | Комментарий |\n"
            "|------|-------|-----|-----------|-------------|\n"
            "| 25.08.2025 | 50000 | Доход | Зарплата | Основная зарплата |\n"
            "| 25.08.2025 | -1500 | Расход | Продукты | Пятёрочка |\n"
            "| 25.08.2025 | -300 | Расход | Транспорт | Такси |\n"
            "| 26.08.2025 | 10000 | Доход | Фриланс | Проект |\n"
            "| 26.08.2025 | -800 | Расход | Развлечения | Кино |\n\n"
            "💡 *Советы:*\n"
            "• Используйте отрицательные числа для расходов\n"
            "• Или указывайте тип 'Расход'/'Доход'\n"
            "• Категории можно группировать (Продукты, Транспорт, Развлечения)\n"
            "• Комментарии помогают понять детали операции",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Подключить таблицу", callback_data='finance_connect')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_format_requirements')]
            ])
        )
        return 'show_template'
    
    @staticmethod
    async def handle_demo_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle demo mode activation"""
        query = update.callback_query
        await query.answer()
        
        await FinanceInterface._edit_message_safely(
            query,
            "🎮 *Демо-режим*\n\n"
            "Включаю демо: 3 месяца операций, 8 категорий, еженедельная динамика.\n\n"
            "📊 *Демо-данные включают:*\n"
            "• 3 месяца финансовых операций\n"
            "• 8 основных категорий\n"
            "• Еженедельная динамика\n"
            "• Реалистичные суммы и категории\n\n"
            "✅ *Это не сохраняется и не влияет на твои данные.*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Показать аналитику", callback_data='finance_demo_analysis')],
                [InlineKeyboardButton("🔗 Я готов подключить свою таблицу", callback_data='finance_connect')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
            ])
        )
        return 'demo_mode'
    
    @staticmethod
    async def handle_demo_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle demo analysis display"""
        query = update.callback_query
        await query.answer()
        
        # Generate demo data analysis
        demo_analysis = finance_service.generate_demo_analysis()
        
        message = "📊 *Демо-анализ за последние 3 месяца*\n\n"
        message += f"💰 *Общая статистика:*\n"
        message += f"• Доходы: {demo_analysis['total_income']:,.0f} ₽\n"
        message += f"• Расходы: {demo_analysis['total_expenses']:,.0f} ₽\n"
        message += f"• Баланс: {demo_analysis['balance']:,.0f} ₽\n"
        message += f"• Операций: {demo_analysis['transactions_count']}\n\n"
        
        if demo_analysis['expense_categories']:
            message += "📉 *Топ расходов по категориям:*\n"
            for i, (category, amount) in enumerate(list(demo_analysis['expense_categories'].items())[:5], 1):
                message += f"{i}. {category}: {amount:,.0f} ₽\n"
            message += "\n"
        
        if demo_analysis['income_categories']:
            message += "📈 *Топ доходов по категориям:*\n"
            for i, (category, amount) in enumerate(list(demo_analysis['income_categories'].items())[:3], 1):
                message += f"{i}. {category}: {amount:,.0f} ₽\n"
            message += "\n"
        
        message += "🎯 *Инсайты:*\n"
        message += "• Самые большие расходы: Продукты и Транспорт\n"
        message += "• Основной доход: Зарплата\n"
        message += "• Рекомендуется оптимизировать траты на развлечения\n\n"
        message += "💡 *Это демо-данные. Подключите свою таблицу для реального анализа!*"
        
        keyboard = [
            [InlineKeyboardButton("📊 Детальный анализ", callback_data='finance_demo_detailed')],
            [InlineKeyboardButton("🔗 Подключить свою таблицу", callback_data='finance_connect')],
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_demo')]
        ]
        
        await FinanceInterface._edit_message_safely(
            query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return 'demo_analysis'
    
    @staticmethod
    async def handle_demo_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle detailed demo analysis"""
        query = update.callback_query
        await query.answer()
        
        demo_analysis = finance_service.generate_demo_analysis()
        
        message = "📊 *Детальный демо-анализ*\n\n"
        
        if demo_analysis['expense_categories']:
            message += "📉 *Все расходы по категориям:*\n"
            for category, amount in demo_analysis['expense_categories'].items():
                percentage = (amount / demo_analysis['total_expenses'] * 100) if demo_analysis['total_expenses'] > 0 else 0
                message += f"• {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"
            message += "\n"
        
        if demo_analysis['income_categories']:
            message += "📈 *Все доходы по категориям:*\n"
            for category, amount in demo_analysis['income_categories'].items():
                percentage = (amount / demo_analysis['total_income'] * 100) if demo_analysis['total_income'] > 0 else 0
                message += f"• {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"
            message += "\n"
        
        message += "📈 *Динамика по неделям:*\n"
        message += "• Неделя 1: +15,000 ₽\n"
        message += "• Неделя 2: +8,500 ₽\n"
        message += "• Неделя 3: +12,300 ₽\n"
        message += "• Неделя 4: +9,200 ₽\n\n"
        
        message += "🎯 *Рекомендации:*\n"
        message += "• Сократить траты на развлечения на 20%\n"
        message += "• Оптимизировать транспортные расходы\n"
        message += "• Увеличить доходы от фриланса\n\n"
        message += "💡 *Это демо-данные. Подключите свою таблицу для реального анализа!*"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к анализу", callback_data='finance_demo_analysis')],
            [InlineKeyboardButton("🔗 Подключить свою таблицу", callback_data='finance_connect')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='finance_menu')]
        ]
        
        await FinanceInterface._edit_message_safely(
            query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return 'demo_detailed'
    
    @staticmethod
    async def handle_sheet_url_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle user input of Google Sheets URL"""
        user_id = update.message.from_user.id
        url = update.message.text.strip()
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            "⏳ Обрабатываю ссылку на таблицу...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data='finance_menu')]
            ])
        )
        
        # Extract sheet ID
        sheet_id = finance_service.extract_sheet_id_from_url(url)
        if not sheet_id:
            await processing_msg.edit_text(
                "❌ *Не удалось извлечь ID таблицы из ссылки*\n\n"
                "🔍 *Возможные причины:*\n"
                "• Неправильный формат ссылки\n"
                "• Ссылка повреждена\n"
                "• Таблица не существует\n\n"
                "📋 *Правильный формат:*\n"
                "`https://docs.google.com/spreadsheets/d/SHEET_ID/edit`\n\n"
                "Попробуйте скопировать ссылку заново из адресной строки браузера.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data='finance_connect')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
            return 'waiting_for_url'
        
        # Get available sheets
        await processing_msg.edit_text("🔗 Проверяю доступ к таблице...")
        sheets = finance_service.get_available_sheets(sheet_id)
        if not sheets:
            await processing_msg.edit_text(
                "❌ *Не удалось получить доступ к таблице*\n\n"
                "🔍 *Возможные причины:*\n"
                "• Таблица не доступна для просмотра всем, у кого есть ссылка\n"
                "• Таблица пустая\n"
                "• Проблемы с интернет-соединением\n\n"
                "📋 *Как исправить:*\n"
                "1. Откройте таблицу в браузере\n"
                "2. Нажмите 'Настройки доступа' (справа вверху)\n"
                "3. Выберите 'Доступно всем, у кого есть ссылка'\n"
                "4. Убедитесь, что в таблице есть данные\n"
                "5. Попробуйте снова",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data='finance_connect')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
            return 'waiting_for_url'
        
        # Store sheet info in context for sheet selection
        context.user_data['temp_sheet_id'] = sheet_id
        context.user_data['temp_sheet_url'] = url
        context.user_data['available_sheets'] = sheets
        
        # Create sheet selection keyboard
        keyboard = []
        for sheet_name in sheets:
            keyboard.append([InlineKeyboardButton(f"📄 {sheet_name}", callback_data=f'finance_select_sheet_{sheet_name}')])
        
        keyboard.extend([
            [InlineKeyboardButton("🔄 Сменить ссылку", callback_data='finance_connect')],
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
        ])
        
        await processing_msg.edit_text(
            "✅ *Ссылка получена!*\n\n"
            f"📊 *Найдено листов:* {len(sheets)}\n\n"
            "Выберите лист, где лежат данные:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Clear waiting state
        context.user_data.pop('waiting_for', None)
        return 'selecting_sheet'
    
    @staticmethod
    async def handle_sheet_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, sheet_name: str) -> str:
        """Handle sheet selection and validation"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        sheet_id = context.user_data.get('temp_sheet_id')
        sheet_url = context.user_data.get('temp_sheet_url')
        
        if not sheet_id:
            await FinanceInterface._edit_message_safely(
                query,
                "❌ Ошибка: данные о таблице потеряны.\n\n"
                "Попробуйте подключить таблицу заново.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Подключить заново", callback_data='finance_connect')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
            return 'finance_menu'
        
        # Show validation message
        await FinanceInterface._edit_message_safely(
            query,
            f"🔍 Проверяю столбцы в листе '{sheet_name}'...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_connect')]
            ])
        )
        
        try:
            # Get and validate sheet data
            raw_data = finance_service.get_sheet_data(sheet_id, sheet_name)
            if not raw_data:
                await FinanceInterface._edit_message_safely(
                    query,
                    f"❌ *Не удалось получить данные из листа '{sheet_name}'*\n\n"
                    "Возможно, лист пустой или недоступен.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Выбрать другой лист", callback_data='finance_connect')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                    ])
                )
                return 'selecting_sheet'
            
            # Parse and validate data
            parsed_data = finance_service.parse_financial_data(raw_data)
            validation_result = finance_service.validate_financial_data(raw_data)
            
            if validation_result['is_valid']:
                # Success - save settings and show success message
                success = db.update_finance_settings(user_id, sheet_url, sheet_name)
                if success:
                    await FinanceInterface._edit_message_safely(
                        query,
                        f"✅ *Лист '{sheet_name}' подключен!*\n\n"
                        f"🔍 *Проверка столбцов:*\n"
                        f"• Найдено: {', '.join(validation_result['found_columns'])}\n"
                        f"• Операций: {len(parsed_data)}\n"
                        f"• Период: {min([r['date'] for r in parsed_data if r.get('date')])} - {max([r['date'] for r in parsed_data if r.get('date')])}\n\n"
                        f"🎉 *Готово к анализу!*",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📊 Запустить анализ", callback_data='finance_menu')],
                            [InlineKeyboardButton("🔄 Изменить лист", callback_data='finance_connect')],
                            [InlineKeyboardButton("📋 Требования к формату", callback_data='finance_format_requirements')]
                        ])
                    )
                    # Clear temporary data
                    context.user_data.pop('temp_sheet_id', None)
                    context.user_data.pop('temp_sheet_url', None)
                    context.user_data.pop('available_sheets', None)
                    return 'finance_menu'
                else:
                    await FinanceInterface._edit_message_safely(
                        query,
                        "❌ *Ошибка при сохранении настроек*\n\n"
                        "Попробуйте еще раз или обратитесь к администратору.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Попробовать снова", callback_data='finance_connect')],
                            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                        ])
                    )
                    return 'selecting_sheet'
            else:
                # Validation failed - show error
                missing_columns = validation_result.get('missing_columns', [])
                found_columns = validation_result.get('found_columns', [])
                
                error_message = f"❌ *Не удалось распознать финансовые данные*\n\n"
                error_message += f"🔍 *Проблема:* Не найдены обязательные столбцы\n\n"
                
                if found_columns:
                    error_message += f"✅ *Найдено:* {', '.join(found_columns)}\n\n"
                
                if missing_columns:
                    error_message += f"❌ *Отсутствует:* {', '.join(missing_columns)}\n\n"
                
                error_message += "📋 *Требуемые столбцы:*\n"
                error_message += "• **Дата** (формат: ДД.ММ.ГГГГ)\n"
                error_message += "• **Сумма** (числовое значение)\n"
                error_message += "• **Тип** (Доход/Расход)\n"
                error_message += "• **Категория** (название категории)\n\n"
                error_message += "📝 *Пример строки:*\n"
                error_message += "`2025-08-25 | -1200 | Расход | Продукты | Пятёрочка`"
                
                await FinanceInterface._edit_message_safely(
                    query,
                    error_message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📄 Показать пример шаблона", callback_data='finance_show_template')],
                        [InlineKeyboardButton("🔄 Проверить снова", callback_data=f'finance_select_sheet_{sheet_name}')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_connect')]
                    ])
                )
                return 'selecting_sheet'
                
        except Exception as e:
            logger.error(f"Error validating sheet {sheet_name} for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(
                query,
                "❌ *Ошибка при проверке данных*\n\n"
                "Попробуйте позже или проверьте формат таблицы.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data='finance_connect')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
            return 'selecting_sheet'
    
    @staticmethod
    async def handle_show_sheet_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle showing current sheet URL"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            if finance_settings:
                await query.edit_message_caption(
                    caption=f"🔗 *Текущая таблица*\n\n"
                    f"`{finance_settings['url']}`\n"
                    f"📄 Лист: `{finance_settings['sheet_name']}`\n\n"
                    f"Чтобы изменить, нажмите 'Указать ссылку на таблицу'",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Изменить", callback_data='finance_connect')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                    ]),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_caption(
                    caption="❌ Таблица не настроена.\n\n"
                    "Нажмите 'Указать ссылку на таблицу' для настройки.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Настроить", callback_data='finance_connect')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                    ])
                )
        else:
            if finance_settings:
                await FinanceInterface._edit_message_safely(query, 
                    f"🔗 *Текущая таблица*\n\n"
                    f"`{finance_settings['url']}`\n"
                    f"📄 Лист: `{finance_settings['sheet_name']}`\n\n"
                    f"Чтобы изменить, нажмите 'Указать ссылку на таблицу'",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Изменить", callback_data='finance_connect')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                    ]),
                    parse_mode='Markdown'
                )
            else:
                await FinanceInterface._edit_message_safely(query, 
                    "❌ Таблица не настроена.\n\n"
                    "Нажмите 'Указать ссылку на таблицу' для настройки.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Настроить", callback_data='finance_connect')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                    ])
                )
        
        return 'finance_settings'
    
    @staticmethod
    async def handle_clear_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle clearing finance settings"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        success = db.update_finance_settings(user_id, None)
        
        if success:
            await FinanceInterface._edit_message_safely(query, 
                "✅ Настройки финансов удалены.\n\n"
                "Вы можете настроить новую таблицу в любое время.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Настроить заново", callback_data='finance_set_url')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
        else:
            await FinanceInterface._edit_message_safely(query, 
                "❌ Ошибка при удалении настроек.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                ])
            )
        
        return 'finance_settings'
    
    @staticmethod
    async def handle_finance_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str) -> str:
        """Handle finance analysis for specific period"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        if not finance_settings:
            await FinanceInterface._edit_message_safely(query, 
                "❌ Таблица не настроена.\n\n"
                "Сначала настройте Google Sheets в настройках.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Настройки", callback_data='finance_settings')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
            return 'finance_menu'
        
        # Show loading message
        await FinanceInterface._edit_message_safely(query, 
            "⏳ Загружаю данные из таблицы...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
            ])
        )
        
        try:
            # Get data from sheet
            sheet_id = finance_service.extract_sheet_id_from_url(finance_settings['url'])
            raw_data = finance_service.get_sheet_data(sheet_id, finance_settings['sheet_name'])
            
            if not raw_data:
                await FinanceInterface._edit_message_safely(query, 
                    "❌ Не удалось получить данные из таблицы.\n\n"
                    "Проверьте настройки таблицы.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Настройки", callback_data='finance_settings')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                    ])
                )
                return 'finance_menu'
            
            # Parse and analyze data
            parsed_data = finance_service.parse_financial_data(raw_data)
            analysis = finance_service.analyze_finances(parsed_data, period)
            
            # Format response
            period_names = {
                'day': 'день',
                'week': 'неделю', 
                'month': 'месяц',
                'year': 'год',
                'all': 'все время'
            }
            
            period_name = period_names.get(period, period)
            
            message = f"💰 *Анализ за {period_name}*\n\n"
            message += f"📊 *Общая статистика:*\n"
            message += f"• Доходы: {analysis['total_income']:,.0f} ₽\n"
            message += f"• Расходы: {analysis['total_expenses']:,.0f} ₽\n"
            message += f"• Баланс: {analysis['balance']:,.0f} ₽\n"
            message += f"• Операций: {analysis['transactions_count']}\n\n"
            
            if analysis['expense_categories']:
                message += "📉 *Топ расходов по категориям:*\n"
                for i, (category, amount) in enumerate(list(analysis['expense_categories'].items())[:5], 1):
                    message += f"{i}. {category}: {amount:,.0f} ₽\n"
                message += "\n"
            
            if analysis['income_categories']:
                message += "📈 *Топ доходов по категориям:*\n"
                for i, (category, amount) in enumerate(list(analysis['income_categories'].items())[:5], 1):
                    message += f"{i}. {category}: {amount:,.0f} ₽\n"
            
            keyboard = [
                [InlineKeyboardButton("📊 Детальный анализ", callback_data=f'finance_detailed_{period}')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
            ]
            
            await FinanceInterface._edit_message_safely(query, 
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error analyzing finances for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(query, 
                "❌ Ошибка при анализе данных.\n\n"
                "Попробуйте позже или проверьте настройки таблицы.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Настройки", callback_data='finance_settings')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
        
        return 'finance_menu'
    
    @staticmethod
    async def handle_detailed_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str) -> str:
        """Handle detailed finance analysis"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        sheet_url = db.get_finance_settings(user_id)
        
        try:
            sheet_id = finance_service.extract_sheet_id_from_url(sheet_url)
            raw_data = finance_service.get_sheet_data(sheet_id)
            parsed_data = finance_service.parse_financial_data(raw_data)
            analysis = finance_service.analyze_finances(parsed_data, period)
            
            period_names = {
                'day': 'день',
                'week': 'неделю', 
                'month': 'месяц',
                'year': 'год',
                'all': 'все время'
            }
            
            period_name = period_names.get(period, period)
            
            message = f"📊 *Детальный анализ за {period_name}*\n\n"
            
            if analysis['expense_categories']:
                message += "📉 *Все расходы по категориям:*\n"
                for category, amount in analysis['expense_categories'].items():
                    percentage = (amount / analysis['total_expenses'] * 100) if analysis['total_expenses'] > 0 else 0
                    message += f"• {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"
                message += "\n"
            
            if analysis['income_categories']:
                message += "📈 *Все доходы по категориям:*\n"
                for category, amount in analysis['income_categories'].items():
                    percentage = (amount / analysis['total_income'] * 100) if analysis['total_income'] > 0 else 0
                    message += f"• {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к анализу", callback_data=f'finance_{period}')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='finance_menu')]
            ]
            
            await FinanceInterface._edit_message_safely(query, 
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in detailed analysis for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(query, 
                "❌ Ошибка при детальном анализе.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
        
        return 'finance_menu'

    @staticmethod
    async def handle_monthly_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle monthly analytics display"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        # Show loading message
        await FinanceInterface._edit_message_safely(
            query,
            "⏳ Анализирую данные за месяц...",
            reply_markup=FinanceInterface.create_navigation_keyboard('finance_menu')
        )
        
        try:
            # Get data and analysis
            sheet_id = finance_service.extract_sheet_id_from_url(finance_settings['url'])
            raw_data = finance_service.get_sheet_data(sheet_id, finance_settings['sheet_name'])
            parsed_data = finance_service.parse_financial_data(raw_data)
            month_analysis = finance_service.analyze_finances(parsed_data, 'month')
            unusual_expenses = finance_service.get_unusual_expenses(parsed_data, 'month')
            
            # Get current month name
            current_month = datetime.now().strftime('%B')
            
            # Calculate average daily expenses
            avg_daily_expenses = month_analysis['total_expenses'] / 30 if month_analysis['total_expenses'] > 0 else 0
            
            # Format message
            message = f"📊 *Аналитика за {current_month}*\n\n"
            
            # Monthly summary
            message += f"💰 *Общая статистика:*\n"
            message += f"• Расходы: {month_analysis['total_expenses']:,.0f} ₽\n"
            message += f"• Доходы: {month_analysis['total_income']:,.0f} ₽\n"
            message += f"• Среднедневные расходы: {avg_daily_expenses:,.0f} ₽\n"
            message += f"• Операций: {month_analysis['transactions_count']}\n\n"
            
            # Unusual expenses
            if unusual_expenses:
                message += "⚠️ *Нетипичные дни:*\n"
                for i, unusual in enumerate(unusual_expenses[:3], 1):
                    date_str = unusual['date'].strftime('%d %b')
                    category = unusual['largest_transaction'].get('main_category', 'Неизвестно')
                    message += f"{i}. {date_str} ({unusual['total_amount']:,.0f} ₽ — {category})\n"
                message += "\n"
            
            # Top categories
            if month_analysis['expense_categories']:
                message += "📉 *Топ категорий расходов:*\n"
                for i, (category, amount) in enumerate(list(month_analysis['expense_categories'].items())[:5], 1):
                    percentage = (amount / month_analysis['total_expenses'] * 100) if month_analysis['total_expenses'] > 0 else 0
                    message += f"{i}. {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"
            
            # Keyboard
            keyboard = [
                [InlineKeyboardButton("📅 Предыдущий месяц", callback_data='finance_previous_month')],
                [InlineKeyboardButton("📊 Сравнить с прошлым годом", callback_data='finance_year_comparison')],
                [InlineKeyboardButton("⚠️ Нетипичные траты", callback_data='finance_unusual_expenses')],
                [InlineKeyboardButton("📄 Экспорт отчёта", callback_data='finance_export_report')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            await FinanceInterface._edit_message_safely(
                query,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in monthly analytics for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(
                query,
                "❌ Ошибка при анализе данных за месяц.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ])
            )
        
        return 'monthly_analytics'
    
    @staticmethod
    async def handle_categories_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle categories analysis display"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        # Show loading message
        await FinanceInterface._edit_message_safely(
            query,
            "⏳ Анализирую категории...",
            reply_markup=FinanceInterface.create_navigation_keyboard('finance_menu')
        )
        
        try:
            # Get data and analysis
            sheet_id = finance_service.extract_sheet_id_from_url(finance_settings['url'])
            raw_data = finance_service.get_sheet_data(sheet_id, finance_settings['sheet_name'])
            parsed_data = finance_service.parse_financial_data(raw_data)
            month_analysis = finance_service.analyze_finances(parsed_data, 'month')
            growth_analysis = finance_service.get_category_growth_analysis(parsed_data, 3)
            
            # Format message
            message = "📋 *Анализ по категориям*\n\n"
            
            # Top categories
            if month_analysis['expense_categories']:
                message += "🏆 *Топ-5 категорий:*\n\n"
                for i, (category, amount) in enumerate(list(month_analysis['expense_categories'].items())[:5], 1):
                    percentage = (amount / month_analysis['total_expenses'] * 100) if month_analysis['total_expenses'] > 0 else 0
                    message += f"{i}. **{category}** — {amount:,.0f} ₽ ({percentage:.1f}%)\n"
                message += "\n"
            
            # Growth leaders
            if growth_analysis['fastest_growing']:
                message += "📈 *Лидеры роста (3 месяца):*\n"
                for growth in growth_analysis['fastest_growing'][:3]:
                    message += f"• {growth['category']}: +{growth['growth_rate']:.1f}%\n"
                message += "\n"
            
            # Declining categories
            if growth_analysis['declining']:
                message += "📉 *Снижающиеся категории:*\n"
                for decline in growth_analysis['declining'][:3]:
                    message += f"• {decline['category']}: {decline['growth_rate']:.1f}%\n"
                message += "\n"
            
            message += "💡 *Советы:*\n"
            message += "• Нажмите на категорию для детализации\n"
            message += "• Используйте 'Изменить категории' для группировки\n"
            message += "• Сравните с прошлыми месяцами"
            
            # Create keyboard with top categories
            keyboard = []
            if month_analysis['expense_categories']:
                for category in list(month_analysis['expense_categories'].keys())[:3]:
                    keyboard.append([InlineKeyboardButton(f"📊 {category}", callback_data=f'finance_category_detail_{category}')])
            
            keyboard.extend([
                [InlineKeyboardButton("✏️ Изменить/объединить категории", callback_data='finance_edit_categories')],
                [InlineKeyboardButton("📊 Сравнить 3 месяца", callback_data='finance_compare_months')],
                [InlineKeyboardButton("📈 Лидеры роста", callback_data='finance_growth_leaders')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ])
            
            await FinanceInterface._edit_message_safely(
                query,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in categories analysis for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(
                query,
                "❌ Ошибка при анализе категорий.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
        
        return 'categories_analysis'
    
    @staticmethod
    async def handle_trends_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle trends and forecast analysis"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        # Show loading message
        await FinanceInterface._edit_message_safely(
            query,
            "⏳ Анализирую тренды и прогнозы...",
            reply_markup=FinanceInterface.create_navigation_keyboard('finance_menu')
        )
        
        try:
            # Get data and analysis
            sheet_id = finance_service.extract_sheet_id_from_url(finance_settings['url'])
            raw_data = finance_service.get_sheet_data(sheet_id, finance_settings['sheet_name'])
            parsed_data = finance_service.parse_financial_data(raw_data)
            
            # Get various analyses
            week_analysis = finance_service.analyze_finances(parsed_data, 'week')
            previous_week = finance_service.get_previous_period_analysis(parsed_data, 'week')
            forecast = finance_service.get_expense_forecast(parsed_data, 30)
            
            # Calculate week trend
            week_trend = 0
            if previous_week['total_expenses'] > 0:
                week_trend = ((week_analysis['total_expenses'] - previous_week['total_expenses']) / 
                             previous_week['total_expenses']) * 100
            
            # Format message
            message = "📈 *Тренды и прогнозы*\n\n"
            
            # Weekly trend
            trend_icon = "↓" if week_trend < 0 else "↑"
            message += f"📊 *Динамика 12 недель:*\n"
            message += f"• Текущая неделя: {week_analysis['total_expenses']:,.0f} ₽\n"
            message += f"• Предыдущая неделя: {previous_week['total_expenses']:,.0f} ₽\n"
            message += f"• Изменение: {trend_icon} {abs(week_trend):.1f}%\n\n"
            
            # Forecast
            message += f"🔮 *Прогноз на остаток месяца:*\n"
            message += f"• Ожидаемые расходы: {forecast['forecast_amount']:,.0f} ₽\n"
            message += f"• Погрешность: ±{forecast['confidence_interval']:,.0f} ₽\n"
            message += f"• Тренд: {forecast['trend']}\n\n"
            
            # Factors
            if forecast['factors']:
                message += "📋 *Учтённые факторы:*\n"
                for factor in forecast['factors']:
                    message += f"• {factor}\n"
                message += "\n"
            
            # Recommendations
            message += "💡 *Рекомендации:*\n"
            if week_trend > 10:
                message += "• Расходы растут - рассмотрите оптимизацию\n"
            elif week_trend < -10:
                message += "• Отличная экономия! Продолжайте в том же духе\n"
            else:
                message += "• Расходы стабильны - можно планировать бюджет\n"
            
            # Keyboard
            keyboard = [
                [InlineKeyboardButton("🔍 Факторы перерасхода", callback_data='finance_overspending_factors')],
                [InlineKeyboardButton("💡 Советы по экономии", callback_data='finance_savings_tips')],
                [InlineKeyboardButton("🎯 Установить цель", callback_data='finance_set_goal')],
                [InlineKeyboardButton("📊 Сравнить с прошлым месяцем", callback_data='finance_month_comparison')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            await FinanceInterface._edit_message_safely(
                query,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in trends analysis for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(
                query,
                "❌ Ошибка при анализе трендов.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
        
        return 'trends_analysis'
    
    @staticmethod
    async def handle_budgets_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle budgets and limits management"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Get user budgets from database
        user_budgets = db.get_user_budgets(user_id)
        
        if not user_budgets:
            message = "💰 *Бюджеты и лимиты*\n\n"
            message += "У вас пока нет настроенных бюджетов.\n\n"
            message += "💡 *Что дают бюджеты:*\n"
            message += "• Контроль расходов по категориям\n"
            message += "• Уведомления о приближении к лимиту\n"
            message += "• Анализ перерасхода\n"
            message += "• Помощь в планировании"
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить бюджет", callback_data='finance_add_budget')],
                [InlineKeyboardButton("📋 Примеры бюджетов", callback_data='finance_budget_examples')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
        else:
            # Show current budgets with progress
            message = "💰 *Ваши бюджеты:*\n\n"
            
            for budget in user_budgets:
                progress_percentage = (budget['spent'] / budget['limit'] * 100) if budget['limit'] > 0 else 0
                progress_bar = "█" * min(int(progress_percentage / 10), 10) + "░" * (10 - min(int(progress_percentage / 10), 10))
                
                message += f"📊 **{budget['category']}**\n"
                message += f"Лимит: {budget['limit']:,.0f} ₽\n"
                message += f"Потрачено: {budget['spent']:,.0f} ₽ ({progress_percentage:.1f}%)\n"
                message += f"Осталось: {budget['limit'] - budget['spent']:,.0f} ₽\n"
                message += f"[{progress_bar}]\n"
                
                if progress_percentage > 90:
                    message += "⚠️ *Близко к лимиту!*\n"
                elif progress_percentage > 80:
                    message += "⚡ *Внимание!*\n"
                
                message += "\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить бюджет", callback_data='finance_add_budget')],
                [InlineKeyboardButton("✏️ Изменить бюджет", callback_data='finance_edit_budget')],
                [InlineKeyboardButton("🔔 Уведомления о перерасходе", callback_data='finance_overspending_alerts')],
                [InlineKeyboardButton("🔄 Обнулить в новом месяце", callback_data='finance_reset_budgets')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
        
        await FinanceInterface._edit_message_safely(
            query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return 'budgets_management'
    
    @staticmethod
    async def handle_search_operations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle search operations interface"""
        query = update.callback_query
        await query.answer()
        
        message = "🔍 *Поиск по операциям*\n\n"
        message += "Задайте вопрос простым языком:\n\n"
        message += "📝 *Примеры запросов:*\n"
        message += "• \"Покажи траты на кофе за июль\"\n"
        message += "• \"Сколько подписки в этом месяце?\"\n"
        message += "• \"Самая крупная трата за неделю\"\n"
        message += "• \"Сводка за выходные\"\n"
        message += "• \"Траты на транспорт в августе\"\n\n"
        message += "💡 *Советы:*\n"
        message += "• Используйте названия категорий\n"
        message += "• Указывайте периоды (день, неделя, месяц)\n"
        message += "• Можно искать по описаниям операций"
        
        # Set user state to wait for search query
        context.user_data['waiting_for'] = 'waiting_for_finance_search'
        
        keyboard = [
            [InlineKeyboardButton("📋 Популярные запросы", callback_data='finance_popular_queries')],
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        
        await FinanceInterface._edit_message_safely(
            query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return 'search_operations'
    
    @staticmethod
    async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str) -> str:
        """Handle search query from user"""
        user_id = update.message.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        if not finance_settings:
            await update.message.reply_text(
                "❌ Таблица не настроена.\n\n"
                "Сначала подключите Google Sheets для поиска по операциям.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Подключить таблицу", callback_data='finance_connect')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
            return 'search_operations'
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            "🔍 Ищу операции...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data='finance_search')]
            ])
        )
        
        try:
            # Get data
            sheet_id = finance_service.extract_sheet_id_from_url(finance_settings['url'])
            raw_data = finance_service.get_sheet_data(sheet_id, finance_settings['sheet_name'])
            parsed_data = finance_service.parse_financial_data(raw_data)
            
            # Process search query
            search_results = finance_service.search_operations(parsed_data, query_text)
            
            if not search_results['operations']:
                await processing_msg.edit_text(
                    f"🔍 *Результаты поиска: \"{query_text}\"*\n\n"
                    f"❌ Операции не найдены.\n\n"
                    f"💡 *Попробуйте:*\n"
                    f"• Изменить ключевые слова\n"
                    f"• Использовать названия категорий\n"
                    f"• Указать период (месяц, неделя)\n"
                    f"• Поискать по описаниям",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔍 Новый поиск", callback_data='finance_search')],
                        [InlineKeyboardButton("📋 Популярные запросы", callback_data='finance_popular_queries')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                    ])
                )
                return 'search_operations'
            
            # Format results
            message = f"🔍 *Результаты поиска: \"{query_text}\"*\n\n"
            
            # Summary
            total_amount = sum(op['amount'] for op in search_results['operations'])
            message += f"📊 *Найдено:* {len(search_results['operations'])} операций\n"
            message += f"💰 *Общая сумма:* {total_amount:,.0f} ₽\n"
            message += f"📅 *Период:* {search_results['period']}\n\n"
            
            # Top operations
            if search_results['operations']:
                message += "🏆 *Крупные операции:*\n"
                for i, op in enumerate(search_results['operations'][:5], 1):
                    date_str = op['date'].strftime('%d %b')
                    category = op.get('main_category', 'Неизвестно')
                    message += f"{i}. {date_str}: {op['amount']:,.0f} ₽ ({category})\n"
                message += "\n"
            
            # Categories breakdown
            if search_results['categories']:
                message += "📋 *По категориям:*\n"
                for category, amount in list(search_results['categories'].items())[:5]:
                    percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                    message += f"• {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"
            
            # Clear waiting state
            context.user_data.pop('waiting_for', None)
            
            # Keyboard
            keyboard = [
                [InlineKeyboardButton("📄 Экспорт .CSV", callback_data='finance_export_search')],
                [InlineKeyboardButton("📋 Показать все операции", callback_data='finance_show_all_operations')],
                [InlineKeyboardButton("💰 Добавить лимит", callback_data='finance_add_limit_from_search')],
                [InlineKeyboardButton("🔍 Новый поиск", callback_data='finance_search')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            await processing_msg.edit_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error processing search query for user {user_id}: {e}")
            await processing_msg.edit_text(
                "❌ Ошибка при поиске операций.\n\n"
                "Попробуйте изменить запрос или обратитесь к администратору.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Попробовать снова", callback_data='finance_search')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
                ])
            )
        
        return 'search_operations'
    
    @staticmethod
    async def handle_refresh_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle data refresh"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        finance_settings = db.get_finance_settings(user_id)
        
        # Show refreshing message
        await FinanceInterface._edit_message_safely(
            query,
            "🔄 Обновляю данные из таблицы...",
            reply_markup=FinanceInterface.create_navigation_keyboard('finance_menu')
        )
        
        try:
            # Get fresh data
            sheet_id = finance_service.extract_sheet_id_from_url(finance_settings['url'])
            raw_data = finance_service.get_sheet_data(sheet_id, finance_settings['sheet_name'])
            parsed_data = finance_service.parse_financial_data(raw_data)
            
            # Get previous data count for comparison
            previous_count = db.get_user_data_count(user_id)
            current_count = len(parsed_data)
            new_operations = current_count - previous_count
            
            # Update data count in database
            db.update_user_data_count(user_id, current_count)
            
            # Format success message
            current_time = datetime.now().strftime('%d %b, %H:%M')
            message = f"✅ *Данные обновлены!*\n\n"
            message += f"📊 *Статистика:*\n"
            message += f"• Всего операций: {current_count}\n"
            message += f"• Новых операций: {new_operations}\n"
            message += f"• Актуально на: {current_time}\n\n"
            
            if new_operations > 0:
                message += f"🎉 Добавлено {new_operations} новых операций!\n\n"
            else:
                message += "📋 Новых операций не найдено.\n\n"
            
            message += "💡 *Что дальше:*\n"
            message += "• Посмотрите обновленный дайджест\n"
            message += "• Настройте автообновление\n"
            message += "• Проверьте новые тренды"
            
            keyboard = [
                [InlineKeyboardButton("📊 Обновленный дайджест", callback_data='finance_menu')],
                [InlineKeyboardButton("⏰ Запланировать автообновление", callback_data='finance_auto_refresh')],
                [InlineKeyboardButton("📋 Показать изменения", callback_data='finance_show_changes')],
                [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            await FinanceInterface._edit_message_safely(
                query,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error refreshing data for user {user_id}: {e}")
            await FinanceInterface._edit_message_safely(
                query,
                "❌ Ошибка при обновлении данных.\n\n"
                "Проверьте доступ к таблице и попробуйте снова.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data='finance_refresh')],
                    [InlineKeyboardButton("⚙️ Настройки", callback_data='finance_settings')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ])
            )
        
        return 'refresh_data'
