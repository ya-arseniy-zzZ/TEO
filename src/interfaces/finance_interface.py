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
    async def _edit_message_safely(query, text, reply_markup=None):
        """Safely edit message, handling both text and photo messages"""
        if query.message.photo:
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await FinanceInterface._edit_message_safely(query, 
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
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
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
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
            [InlineKeyboardButton("🔙 Назад", callback_data='finance_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    async def handle_finance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle finance menu selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Check if user has configured Google Sheets
        sheet_url = db.get_finance_settings(user_id)
        if not sheet_url:
            await FinanceInterface._edit_message_safely(
                query,
                "💰 *Финансовый анализ*\n\n"
                "Для начала работы с финансовым анализом нужно настроить Google Sheets.\n\n"
                "Нажмите кнопку ниже, чтобы указать ссылку на вашу таблицу:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Настройки", callback_data='finance_settings')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
                ])
            )
            return 'finance_menu'
        
        await FinanceInterface._edit_message_safely(
            query,
            "💰 *Финансовый анализ*\n\n"
            "Выберите период для анализа ваших финансов:",
            reply_markup=FinanceInterface.create_finance_menu()
        )
        return 'finance_menu'
    
    @staticmethod
    async def handle_finance_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle finance settings menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        sheet_url = db.get_finance_settings(user_id)
        
        if sheet_url:
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
        context.user_data['waiting_for'] = 'finance_sheet_url'
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            await query.edit_message_caption(
                caption="📝 *Настройка Google Sheets*\n\n"
                "Отправьте ссылку на вашу Google таблицу.\n\n"
                "Формат ссылки:\n"
                "`https://docs.google.com/spreadsheets/d/SHEET_ID/edit`\n\n"
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
            "Формат ссылки:\n"
            "`https://docs.google.com/spreadsheets/d/SHEET_ID/edit`\n\n"
            "⚠️ *Важно:* Таблица должна быть доступна для просмотра всем, у кого есть ссылка.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data='finance_settings')]
            ])
        )
        return 'waiting_for_url'
    
    @staticmethod
    async def handle_sheet_url_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle user input of Google Sheets URL"""
        user_id = update.message.from_user.id
        url = update.message.text.strip()
        
        # Extract sheet ID
        sheet_id = finance_service.extract_sheet_id_from_url(url)
        if not sheet_id:
            await update.message.reply_text(
                "❌ Не удалось извлечь ID таблицы из ссылки.\n\n"
                "Проверьте, что ссылка корректная и имеет формат:\n"
                "`https://docs.google.com/spreadsheets/d/SHEET_ID/edit`",
                parse_mode='Markdown'
            )
            return 'waiting_for_url'
        
        # Test connection to sheet
        raw_data = finance_service.get_sheet_data(sheet_id)
        if not raw_data:
            await update.message.reply_text(
                "❌ Не удалось получить данные из таблицы.\n\n"
                "Убедитесь, что:\n"
                "• Таблица доступна для просмотра всем, у кого есть ссылка\n"
                "• В таблице есть данные\n"
                "• Ссылка корректная"
            )
            return 'waiting_for_url'
        
        # Parse data to check if it's financial data
        parsed_data = finance_service.parse_financial_data(raw_data)
        if not parsed_data:
            await update.message.reply_text(
                "❌ Не удалось распознать финансовые данные в таблице.\n\n"
                "Убедитесь, что таблица содержит колонки:\n"
                "• Дата\n"
                "• Сумма\n"
                "• Тип (Доход/Расход)\n"
                "• Основная категория"
            )
            return 'waiting_for_url'
        
        # Save settings
        success = db.update_finance_settings(user_id, url)
        if success:
            await update.message.reply_text(
                f"✅ Таблица успешно настроена!\n\n"
                f"Найдено записей: {len(parsed_data)}\n\n"
                f"Теперь вы можете анализировать ваши финансы.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Анализ финансов", callback_data='finance_menu')]
                ])
            )
            # Clear waiting state
            context.user_data.pop('waiting_for', None)
            return 'finance_menu'
        else:
            await update.message.reply_text(
                "❌ Ошибка при сохранении настроек. Попробуйте еще раз."
            )
            return 'waiting_for_url'
    
    @staticmethod
    async def handle_show_sheet_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle showing current sheet URL"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        sheet_url = db.get_finance_settings(user_id)
        
        # Check if the current message has media and handle accordingly
        if query.message.photo:
            if sheet_url:
                await query.edit_message_caption(
                    caption=f"🔗 *Текущая таблица*\n\n"
                    f"`{sheet_url}`\n\n"
                    f"Чтобы изменить, нажмите 'Указать ссылку на таблицу'",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Изменить", callback_data='finance_set_url')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                    ]),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_caption(
                    caption="❌ Таблица не настроена.\n\n"
                    "Нажмите 'Указать ссылку на таблицу' для настройки.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Настроить", callback_data='finance_set_url')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                    ])
                )
        else:
            if sheet_url:
                await FinanceInterface._edit_message_safely(query, 
                    f"🔗 *Текущая таблица*\n\n"
                    f"`{sheet_url}`\n\n"
                    f"Чтобы изменить, нажмите 'Указать ссылку на таблицу'",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Изменить", callback_data='finance_set_url')],
                        [InlineKeyboardButton("🔙 Назад", callback_data='finance_settings')]
                    ]),
                    parse_mode='Markdown'
                )
            else:
                await FinanceInterface._edit_message_safely(query, 
                    "❌ Таблица не настроена.\n\n"
                    "Нажмите 'Указать ссылку на таблицу' для настройки.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Настроить", callback_data='finance_set_url')],
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
        sheet_url = db.get_finance_settings(user_id)
        
        if not sheet_url:
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
            sheet_id = finance_service.extract_sheet_id_from_url(sheet_url)
            raw_data = finance_service.get_sheet_data(sheet_id)
            
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
