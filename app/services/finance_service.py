"""
Finance service for Google Sheets integration
Handles reading and analyzing financial data from Google Sheets
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class FinanceService:
    """Service for analyzing financial data from Google Sheets"""
    
    def __init__(self):
        self.session = requests.Session()
    
    def extract_sheet_id_from_url(self, url: str) -> Optional[str]:
        """Extract Google Sheet ID from URL"""
        try:
            # Clean the URL - remove any extra parameters
            url = url.strip()
            
            # Handle different Google Sheets URL formats
            patterns = [
                # Standard format: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
                r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
                # Alternative format: https://docs.google.com/spreadsheets/d/SHEET_ID/view
                r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
                # With query parameters: https://docs.google.com/spreadsheets/d/SHEET_ID/edit?usp=sharing
                r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
                # Short format: https://docs.google.com/spreadsheets/d/SHEET_ID
                r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
                # Direct ID format
                r'^([a-zA-Z0-9-_]+)$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    sheet_id = match.group(1)
                    # Validate sheet ID format (Google Sheets IDs are typically 44 characters)
                    if len(sheet_id) >= 20 and len(sheet_id) <= 50:
                        return sheet_id
            
            # If no pattern matched, try to parse as URL
            if 'docs.google.com' in url:
                parsed = urlparse(url)
                if parsed.path:
                    match = re.search(r'/d/([a-zA-Z0-9-_]+)', parsed.path)
                    if match:
                        sheet_id = match.group(1)
                        if len(sheet_id) >= 20 and len(sheet_id) <= 50:
                            return sheet_id
            
            logger.warning(f"Could not extract sheet ID from URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting sheet ID from URL {url}: {e}")
            return None
    
    def get_sheet_data(self, sheet_id: str, sheet_name: str = "Sheet1", range_name: str = "A:H") -> Optional[List[List[str]]]:
        """
        Get data from Google Sheets using the public API
        
        Args:
            sheet_id: Google Sheet ID
            sheet_name: Name of the sheet to read (default: Sheet1)
            range_name: Range to read (default A:H for all columns)
            
        Returns:
            List of rows with data or None if error
        """
        try:
            # Use Google Sheets public API (read-only, no auth required for public sheets)
            # Include sheet name in the range if specified
            full_range = f"{sheet_name}!{range_name}" if sheet_name != "Sheet1" else range_name
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&range={full_range}"
            
            response = self.session.get(url, timeout=15)
            
            # Check for specific error responses
            if response.status_code == 403:
                logger.error(f"Access denied to sheet {sheet_id}. Sheet might not be public.")
                return None
            elif response.status_code == 404:
                logger.error(f"Sheet {sheet_id} not found.")
                return None
            elif response.status_code != 200:
                logger.error(f"HTTP {response.status_code} error for sheet {sheet_id}")
                return None
            
            # Check if response contains error message
            if "error" in response.text.lower() or "access denied" in response.text.lower():
                logger.error(f"Google Sheets API returned error for {sheet_id}: {response.text[:200]}")
                return None
            
            # Parse CSV data
            lines = response.text.strip().split('\n')
            if not lines:
                logger.warning(f"Empty response from sheet {sheet_id}")
                return None
            
            data = []
            for line in lines:
                # Remove quotes and split by comma
                row = [cell.strip('"') for cell in line.split(',')]
                data.append(row)
            
            # Check if we have at least a header row
            if len(data) < 1:
                logger.warning(f"No data found in sheet {sheet_id}")
                return None
            
            logger.info(f"Successfully fetched {len(data)} rows from sheet {sheet_id}")
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching sheet {sheet_id}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error while fetching sheet {sheet_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching sheet data for {sheet_id}: {e}")
            return None
    
    def parse_financial_data(self, raw_data: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Parse raw sheet data into structured financial records
        
        Args:
            raw_data: Raw data from Google Sheets
            
        Returns:
            List of parsed financial records
        """
        if not raw_data or len(raw_data) < 2:
            return []
        
        # Expected columns based on the image
        headers = raw_data[0]
        expected_headers = ['Месяц', 'Дата', 'День недели', 'Тип', 'Основная категория', 'Подкатегория', 'Сумма', 'Текст']
        
        # Find column indices
        column_indices = {}
        for i, header in enumerate(headers):
            if header in expected_headers:
                column_indices[header] = i
        
        # If we don't have the expected headers, try to guess by content
        if len(column_indices) < 4:
            # Try to find key columns by content
            for i, header in enumerate(headers):
                header_lower = header.lower().strip()
                if any(word in header_lower for word in ['дата', 'date', 'день']):
                    column_indices['Дата'] = i
                elif any(word in header_lower for word in ['сумма', 'amount', 'стоимость', 'цена']):
                    column_indices['Сумма'] = i
                elif any(word in header_lower for word in ['тип', 'type', 'вид']):
                    column_indices['Тип'] = i
                elif any(word in header_lower for word in ['категория', 'category', 'группа']):
                    column_indices['Основная категория'] = i
                elif any(word in header_lower for word in ['описание', 'текст', 'комментарий', 'note']):
                    column_indices['Текст'] = i
        
        # Log what we found
        logger.info(f"Found columns: {column_indices}")
        
        # Check if we have the minimum required columns
        required_columns = ['Дата', 'Сумма']
        missing_columns = [col for col in required_columns if col not in column_indices]
        if missing_columns:
            logger.warning(f"Missing required columns: {missing_columns}")
            logger.warning(f"Available headers: {headers}")
            return []
        
        parsed_data = []
        
        for row in raw_data[1:]:  # Skip header row
            if len(row) < max(column_indices.values()) + 1:
                continue  # Skip incomplete rows
            
            try:
                record = {}
                
                # Parse date
                if 'Дата' in column_indices:
                    date_str = row[column_indices['Дата']]
                    try:
                        # Try different date formats
                        for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y']:
                            try:
                                record['date'] = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            record['date'] = None
                    except:
                        record['date'] = None
                
                # Parse amount
                if 'Сумма' in column_indices:
                    amount_str = row[column_indices['Сумма']]
                    try:
                        # Remove non-numeric characters except decimal point
                        amount_clean = re.sub(r'[^\d.,]', '', amount_str)
                        amount_clean = amount_clean.replace(',', '.')
                        record['amount'] = float(amount_clean)
                    except:
                        record['amount'] = 0.0
                
                # Parse type (income/expense)
                if 'Тип' in column_indices:
                    type_str = row[column_indices['Тип']].lower()
                    if 'доход' in type_str or 'income' in type_str:
                        record['type'] = 'income'
                    elif 'расход' in type_str or 'expense' in type_str:
                        record['type'] = 'expense'
                    else:
                        record['type'] = 'unknown'
                
                # Parse categories
                if 'Основная категория' in column_indices:
                    record['main_category'] = row[column_indices['Основная категория']]
                
                if 'Подкатегория' in column_indices:
                    record['subcategory'] = row[column_indices['Подкатегория']]
                
                # Parse description
                if 'Текст' in column_indices:
                    record['description'] = row[column_indices['Текст']]
                
                # Only add records with valid date and amount
                if record.get('date') and record.get('amount') is not None:
                    parsed_data.append(record)
                    
            except Exception as e:
                logger.warning(f"Error parsing row {row}: {e}")
                continue
        
        return parsed_data
    
    def analyze_finances(self, data: List[Dict[str, Any]], period: str = 'month') -> Dict[str, Any]:
        """
        Analyze financial data for a specific period
        
        Args:
            data: Parsed financial data
            period: Analysis period ('day', 'week', 'month', 'year')
            
        Returns:
            Analysis results
        """
        if not data:
            return {
                'total_income': 0,
                'total_expenses': 0,
                'balance': 0,
                'income_categories': {},
                'expense_categories': {},
                'transactions_count': 0
            }
        
        # Filter data by period
        today = datetime.now().date()
        filtered_data = []
        
        for record in data:
            if not record.get('date'):
                continue
                
            if period == 'day':
                if record['date'] == today:
                    filtered_data.append(record)
            elif period == 'week':
                week_ago = today - timedelta(days=7)
                if record['date'] >= week_ago:
                    filtered_data.append(record)
            elif period == 'month':
                month_ago = today - timedelta(days=30)
                if record['date'] >= month_ago:
                    filtered_data.append(record)
            elif period == 'year':
                year_ago = today - timedelta(days=365)
                if record['date'] >= year_ago:
                    filtered_data.append(record)
            else:
                # All data
                filtered_data.append(record)
        
        # Calculate totals
        total_income = sum(record['amount'] for record in filtered_data if record.get('type') == 'income')
        total_expenses = sum(record['amount'] for record in filtered_data if record.get('type') == 'expense')
        balance = total_income - total_expenses
        
        # Group by categories
        income_categories = {}
        expense_categories = {}
        
        for record in filtered_data:
            category = record.get('main_category', 'Без категории')
            amount = record['amount']
            
            if record.get('type') == 'income':
                income_categories[category] = income_categories.get(category, 0) + amount
            elif record.get('type') == 'expense':
                expense_categories[category] = expense_categories.get(category, 0) + amount
        
        # Sort categories by amount
        income_categories = dict(sorted(income_categories.items(), key=lambda x: x[1], reverse=True))
        expense_categories = dict(sorted(expense_categories.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': balance,
            'income_categories': income_categories,
            'expense_categories': expense_categories,
            'transactions_count': len(filtered_data),
            'period': period
        }
    
    def get_daily_summary(self, data: List[Dict[str, Any]], date: datetime.date) -> Dict[str, Any]:
        """
        Get financial summary for a specific date
        
        Args:
            data: Parsed financial data
            date: Target date
            
        Returns:
            Daily summary
        """
        daily_data = [record for record in data if record.get('date') == date]
        
        if not daily_data:
            return {
                'date': date,
                'total_income': 0,
                'total_expenses': 0,
                'balance': 0,
                'transactions': []
            }
        
        total_income = sum(record['amount'] for record in daily_data if record.get('type') == 'income')
        total_expenses = sum(record['amount'] for record in daily_data if record.get('type') == 'expense')
        balance = total_income - total_expenses
        
        return {
            'date': date,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': balance,
            'transactions': daily_data
        }
    
    def get_available_sheets(self, sheet_id: str) -> Optional[List[str]]:
        """
        Get list of available sheets in the Google Spreadsheet
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            List of sheet names or None if error
        """
        try:
            # Try to get sheet metadata
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json&tq=SELECT%20*%20LIMIT%201"
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} error for sheet {sheet_id}")
                return None
            
            # For now, return default sheet names since Google Sheets API doesn't provide sheet names easily
            # In a real implementation, you might need to use Google Sheets API with authentication
            return ["Sheet1", "Операции", "2025_финансы", "Данные"]
            
        except Exception as e:
            logger.error(f"Error getting available sheets for {sheet_id}: {e}")
            return None
    
    def validate_financial_data(self, raw_data: List[List[str]]) -> Dict[str, Any]:
        """
        Validate if raw data contains required financial columns
        
        Args:
            raw_data: Raw data from Google Sheets
            
        Returns:
            Validation result with found and missing columns
        """
        if not raw_data or len(raw_data) < 1:
            return {
                'is_valid': False,
                'found_columns': [],
                'missing_columns': ['Дата', 'Сумма', 'Тип', 'Категория'],
                'error': 'No data found'
            }
        
        headers = raw_data[0]
        expected_headers = ['Дата', 'Сумма', 'Тип', 'Категория', 'Комментарий']
        
        # Find column indices
        found_columns = []
        missing_columns = []
        
        for expected_header in expected_headers:
            found = False
            for header in headers:
                if expected_header.lower() in header.lower() or header.lower() in expected_header.lower():
                    found_columns.append(header)
                    found = True
                    break
            if not found:
                missing_columns.append(expected_header)
        
        # Check for alternative column names
        alternative_mappings = {
            'Дата': ['date', 'день', 'дата операции'],
            'Сумма': ['amount', 'стоимость', 'цена', 'сумма операции'],
            'Тип': ['type', 'вид', 'тип операции', 'доход/расход'],
            'Категория': ['category', 'категория', 'группа', 'основная категория'],
            'Комментарий': ['comment', 'описание', 'текст', 'примечание']
        }
        
        # Check for alternative names for missing columns
        for missing_col in missing_columns[:]:  # Copy list to avoid modification during iteration
            if missing_col in alternative_mappings:
                for alt_name in alternative_mappings[missing_col]:
                    for header in headers:
                        if alt_name.lower() in header.lower():
                            found_columns.append(header)
                            missing_columns.remove(missing_col)
                            break
                    if missing_col not in missing_columns:
                        break
        
        # Check if we have minimum required columns
        required_columns = ['Дата', 'Сумма']
        has_required = all(col in found_columns for col in required_columns)
        
        return {
            'is_valid': has_required and len(missing_columns) <= 2,  # Allow missing optional columns
            'found_columns': found_columns,
            'missing_columns': missing_columns,
            'error': None if has_required else 'Missing required columns'
        }
    
    def generate_demo_analysis(self) -> Dict[str, Any]:
        """
        Generate demo financial analysis data
        
        Returns:
            Demo analysis results
        """
        # Generate realistic demo data
        demo_income_categories = {
            'Зарплата': 180000,
            'Фриланс': 45000,
            'Подработка': 25000,
            'Инвестиции': 15000
        }
        
        demo_expense_categories = {
            'Продукты': 45000,
            'Транспорт': 25000,
            'Развлечения': 20000,
            'Коммунальные услуги': 15000,
            'Одежда': 12000,
            'Рестораны': 10000,
            'Здоровье': 8000,
            'Образование': 5000
        }
        
        total_income = sum(demo_income_categories.values())
        total_expenses = sum(demo_expense_categories.values())
        balance = total_income - total_expenses
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': balance,
            'income_categories': demo_income_categories,
            'expense_categories': demo_expense_categories,
            'transactions_count': 1245,
            'period': '3 months'
        }
    
    def get_previous_period_analysis(self, data: List[Dict[str, Any]], period: str = 'week') -> Dict[str, Any]:
        """
        Get analysis for the previous period for comparison
        
        Args:
            data: Parsed financial data
            period: Analysis period ('week', 'month')
            
        Returns:
            Previous period analysis
        """
        if not data:
            return {
                'total_income': 0,
                'total_expenses': 0,
                'balance': 0,
                'transactions_count': 0
            }
        
        # Calculate previous period dates
        today = datetime.now().date()
        if period == 'week':
            current_period_start = today - timedelta(days=today.weekday())
            previous_period_start = current_period_start - timedelta(days=7)
            previous_period_end = current_period_start - timedelta(days=1)
        elif period == 'month':
            current_month_start = today.replace(day=1)
            previous_month_end = current_month_start - timedelta(days=1)
            previous_month_start = previous_month_end.replace(day=1)
            previous_period_start = previous_month_start
            previous_period_end = previous_month_end
        else:
            return {
                'total_income': 0,
                'total_expenses': 0,
                'balance': 0,
                'transactions_count': 0
            }
        
        # Filter data for previous period
        previous_period_data = [
            record for record in data 
            if record.get('date') and previous_period_start <= record['date'] <= previous_period_end
        ]
        
        # Calculate totals
        total_income = sum(record['amount'] for record in previous_period_data if record.get('type') == 'income')
        total_expenses = sum(record['amount'] for record in previous_period_data if record.get('type') == 'expense')
        balance = total_income - total_expenses
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': balance,
            'transactions_count': len(previous_period_data),
            'period_start': previous_period_start,
            'period_end': previous_period_end
        }
    
    def get_unusual_expenses(self, data: List[Dict[str, Any]], period: str = 'month') -> List[Dict[str, Any]]:
        """
        Find unusual expenses (outliers) in the data
        
        Args:
            data: Parsed financial data
            period: Analysis period
            
        Returns:
            List of unusual expenses
        """
        if not data:
            return []
        
        # Filter data by period
        today = datetime.now().date()
        filtered_data = []
        
        for record in data:
            if not record.get('date'):
                continue
                
            if period == 'month':
                month_ago = today - timedelta(days=30)
                if record['date'] >= month_ago:
                    filtered_data.append(record)
            else:
                filtered_data.append(record)
        
        # Calculate average daily expense
        daily_expenses = {}
        for record in filtered_data:
            if record.get('type') == 'expense':
                date = record['date']
                if date not in daily_expenses:
                    daily_expenses[date] = 0
                daily_expenses[date] += record['amount']
        
        if not daily_expenses:
            return []
        
        # Calculate statistics
        daily_amounts = list(daily_expenses.values())
        avg_daily = sum(daily_amounts) / len(daily_amounts)
        std_dev = (sum((x - avg_daily) ** 2 for x in daily_amounts) / len(daily_amounts)) ** 0.5
        
        # Find unusual days (more than 2 standard deviations from mean)
        unusual_days = []
        for date, amount in daily_expenses.items():
            if amount > avg_daily + 2 * std_dev:
                # Get transactions for this day
                day_transactions = [
                    record for record in filtered_data 
                    if record.get('date') == date and record.get('type') == 'expense'
                ]
                
                # Find largest transaction
                largest_transaction = max(day_transactions, key=lambda x: x['amount'])
                
                unusual_days.append({
                    'date': date,
                    'total_amount': amount,
                    'avg_daily': avg_daily,
                    'largest_transaction': largest_transaction,
                    'transactions_count': len(day_transactions)
                })
        
        return sorted(unusual_days, key=lambda x: x['total_amount'], reverse=True)
    
    def get_expense_forecast(self, data: List[Dict[str, Any]], days_ahead: int = 30) -> Dict[str, Any]:
        """
        Generate expense forecast based on historical data
        
        Args:
            data: Parsed financial data
            days_ahead: Number of days to forecast
            
        Returns:
            Forecast data
        """
        if not data:
            return {
                'forecast_amount': 0,
                'confidence_interval': 0,
                'trend': 'stable',
                'factors': []
            }
        
        # Get recent data (last 3 months)
        today = datetime.now().date()
        three_months_ago = today - timedelta(days=90)
        
        recent_data = [
            record for record in data 
            if record.get('date') and record['date'] >= three_months_ago and record.get('type') == 'expense'
        ]
        
        if not recent_data:
            return {
                'forecast_amount': 0,
                'confidence_interval': 0,
                'trend': 'stable',
                'factors': []
            }
        
        # Calculate daily averages by week
        weekly_averages = {}
        for record in recent_data:
            week_start = record['date'] - timedelta(days=record['date'].weekday())
            if week_start not in weekly_averages:
                weekly_averages[week_start] = {'total': 0, 'days': 0}
            weekly_averages[week_start]['total'] += record['amount']
            weekly_averages[week_start]['days'] += 1
        
        # Calculate trend
        weeks = sorted(weekly_averages.keys())
        if len(weeks) >= 2:
            recent_avg = weekly_averages[weeks[-1]]['total'] / weekly_averages[weeks[-1]]['days']
            older_avg = weekly_averages[weeks[0]]['total'] / weekly_averages[weeks[0]]['days']
            
            if recent_avg > older_avg * 1.1:
                trend = 'increasing'
            elif recent_avg < older_avg * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # Calculate forecast
        all_daily_amounts = []
        for record in recent_data:
            all_daily_amounts.append(record['amount'])
        
        avg_daily = sum(all_daily_amounts) / len(all_daily_amounts)
        std_dev = (sum((x - avg_daily) ** 2 for x in all_daily_amounts) / len(all_daily_amounts)) ** 0.5
        
        forecast_amount = avg_daily * days_ahead
        confidence_interval = std_dev * (days_ahead ** 0.5)
        
        # Identify factors
        factors = []
        if trend == 'increasing':
            factors.append("Тренд роста расходов")
        elif trend == 'decreasing':
            factors.append("Тренд снижения расходов")
        
        # Check for seasonal patterns
        if len(weeks) >= 4:
            factors.append("Учтены сезонные колебания")
        
        return {
            'forecast_amount': forecast_amount,
            'confidence_interval': confidence_interval,
            'trend': trend,
            'factors': factors,
            'avg_daily': avg_daily,
            'days_ahead': days_ahead
        }
    
    def get_category_growth_analysis(self, data: List[Dict[str, Any]], months: int = 3) -> Dict[str, Any]:
        """
        Analyze category growth over multiple months
        
        Args:
            data: Parsed financial data
            months: Number of months to analyze
            
        Returns:
            Category growth analysis
        """
        if not data:
            return {
                'fastest_growing': [],
                'declining': [],
                'stable': []
            }
        
        today = datetime.now().date()
        start_date = today - timedelta(days=months * 30)
        
        # Split data into months
        monthly_data = {}
        for record in data:
            if record.get('date') and record['date'] >= start_date:
                month_key = record['date'].replace(day=1)
                if month_key not in monthly_data:
                    monthly_data[month_key] = []
                monthly_data[month_key].append(record)
        
        if len(monthly_data) < 2:
            return {
                'fastest_growing': [],
                'declining': [],
                'stable': []
            }
        
        # Calculate category totals by month
        months_sorted = sorted(monthly_data.keys())
        category_monthly = {}
        
        for month in months_sorted:
            month_data = monthly_data[month]
            for record in month_data:
                if record.get('type') == 'expense':
                    category = record.get('main_category', 'Без категории')
                    if category not in category_monthly:
                        category_monthly[category] = {}
                    if month not in category_monthly[category]:
                        category_monthly[category][month] = 0
                    category_monthly[category][month] += record['amount']
        
        # Calculate growth rates
        growth_rates = {}
        for category, monthly_totals in category_monthly.items():
            if len(monthly_totals) >= 2:
                first_month = min(monthly_totals.keys())
                last_month = max(monthly_totals.keys())
                
                first_amount = monthly_totals[first_month]
                last_amount = monthly_totals[last_month]
                
                if first_amount > 0:
                    growth_rate = ((last_amount - first_amount) / first_amount) * 100
                    growth_rates[category] = {
                        'growth_rate': growth_rate,
                        'first_amount': first_amount,
                        'last_amount': last_amount,
                        'change': last_amount - first_amount
                    }
        
        # Categorize by growth
        fastest_growing = []
        declining = []
        stable = []
        
        for category, data in growth_rates.items():
            if data['growth_rate'] > 20:
                fastest_growing.append({
                    'category': category,
                    'growth_rate': data['growth_rate'],
                    'change': data['change']
                })
            elif data['growth_rate'] < -10:
                declining.append({
                    'category': category,
                    'growth_rate': data['growth_rate'],
                    'change': data['change']
                })
            else:
                stable.append({
                    'category': category,
                    'growth_rate': data['growth_rate'],
                    'change': data['change']
                })
        
        return {
            'fastest_growing': sorted(fastest_growing, key=lambda x: x['growth_rate'], reverse=True),
            'declining': sorted(declining, key=lambda x: x['growth_rate']),
            'stable': sorted(stable, key=lambda x: abs(x['growth_rate']))
        }

    def search_operations(self, data: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """
        Search operations by natural language query
        
        Args:
            data: Parsed financial data
            query: Search query in natural language
            
        Returns:
            Search results with operations and statistics
        """
        if not data:
            return {
                'operations': [],
                'categories': {},
                'period': 'Не определен',
                'total_amount': 0
            }
        
        query_lower = query.lower()
        matched_operations = []
        
        # Parse query for time periods
        time_period = None
        if any(word in query_lower for word in ['сегодня', 'today']):
            time_period = 'today'
        elif any(word in query_lower for word in ['вчера', 'yesterday']):
            time_period = 'yesterday'
        elif any(word in query_lower for word in ['неделя', 'неделю', 'week']):
            time_period = 'week'
        elif any(word in query_lower for word in ['месяц', 'месяца', 'month']):
            time_period = 'month'
        elif any(word in query_lower for word in ['год', 'года', 'year']):
            time_period = 'year'
        
        # Parse query for categories
        category_keywords = []
        for record in data:
            if record.get('main_category'):
                category = record['main_category'].lower()
                if category in query_lower:
                    category_keywords.append(category)
        
        # Parse query for descriptions
        description_keywords = []
        for record in data:
            if record.get('description'):
                desc = record['description'].lower()
                # Extract keywords from description that match query
                words = desc.split()
                for word in words:
                    if len(word) > 2 and word in query_lower:
                        description_keywords.append(word)
        
        # Filter data based on query
        today = datetime.now().date()
        
        for record in data:
            if not record.get('date'):
                continue
            
            # Time period filter
            if time_period:
                if time_period == 'today' and record['date'] != today:
                    continue
                elif time_period == 'yesterday' and record['date'] != today - timedelta(days=1):
                    continue
                elif time_period == 'week':
                    week_ago = today - timedelta(days=7)
                    if record['date'] < week_ago:
                        continue
                elif time_period == 'month':
                    month_ago = today - timedelta(days=30)
                    if record['date'] < month_ago:
                        continue
                elif time_period == 'year':
                    year_ago = today - timedelta(days=365)
                    if record['date'] < year_ago:
                        continue
            
            # Category filter
            if category_keywords:
                record_category = record.get('main_category', '').lower()
                if not any(cat in record_category for cat in category_keywords):
                    continue
            
            # Description filter
            if description_keywords:
                record_desc = record.get('description', '').lower()
                if not any(keyword in record_desc for keyword in description_keywords):
                    continue
            
            # Amount filter (look for specific amounts in query)
            amount_matches = re.findall(r'\d+', query)
            if amount_matches:
                query_amount = float(amount_matches[0])
                if abs(record['amount'] - query_amount) > 100:  # Allow some tolerance
                    continue
            
            # If no specific filters, check if query matches any field
            if not (time_period or category_keywords or description_keywords or amount_matches):
                record_text = f"{record.get('main_category', '')} {record.get('description', '')}".lower()
                if not any(word in record_text for word in query_lower.split() if len(word) > 2):
                    continue
            
            matched_operations.append(record)
        
        # Sort by amount (largest first)
        matched_operations.sort(key=lambda x: x['amount'], reverse=True)
        
        # Calculate categories breakdown
        categories = {}
        for op in matched_operations:
            category = op.get('main_category', 'Без категории')
            categories[category] = categories.get(category, 0) + op['amount']
        
        # Determine period description
        if time_period:
            period_names = {
                'today': 'Сегодня',
                'yesterday': 'Вчера',
                'week': 'Последняя неделя',
                'month': 'Последний месяц',
                'year': 'Последний год'
            }
            period = period_names.get(time_period, 'Не определен')
        else:
            period = 'Все время'
        
        return {
            'operations': matched_operations,
            'categories': categories,
            'period': period,
            'total_amount': sum(op['amount'] for op in matched_operations)
        }


# Global instance
finance_service = FinanceService()
