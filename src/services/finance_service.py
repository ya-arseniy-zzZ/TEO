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
            # Handle different Google Sheets URL formats
            if '/spreadsheets/d/' in url:
                # Format: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
                match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
                if match:
                    return match.group(1)
            elif 'docs.google.com' in url:
                # Try to parse as URL
                parsed = urlparse(url)
                if parsed.path:
                    match = re.search(r'/d/([a-zA-Z0-9-_]+)', parsed.path)
                    if match:
                        return match.group(1)
            
            # If it's just the ID
            if re.match(r'^[a-zA-Z0-9-_]+$', url):
                return url
                
            return None
        except Exception as e:
            logger.error(f"Error extracting sheet ID from URL {url}: {e}")
            return None
    
    def get_sheet_data(self, sheet_id: str, range_name: str = "A:H") -> Optional[List[List[str]]]:
        """
        Get data from Google Sheets using the public API
        
        Args:
            sheet_id: Google Sheet ID
            range_name: Range to read (default A:H for all columns)
            
        Returns:
            List of rows with data or None if error
        """
        try:
            # Use Google Sheets public API (read-only, no auth required for public sheets)
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&range={range_name}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse CSV data
            lines = response.text.strip().split('\n')
            data = []
            
            for line in lines:
                # Remove quotes and split by comma
                row = [cell.strip('"') for cell in line.split(',')]
                data.append(row)
            
            return data
            
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
        
        # If we don't have the expected headers, try to guess
        if len(column_indices) < 4:
            # Try to find key columns by content
            for i, header in enumerate(headers):
                if 'дата' in header.lower() or 'date' in header.lower():
                    column_indices['Дата'] = i
                elif 'сумма' in header.lower() or 'amount' in header.lower():
                    column_indices['Сумма'] = i
                elif 'тип' in header.lower() or 'type' in header.lower():
                    column_indices['Тип'] = i
                elif 'категория' in header.lower() or 'category' in header.lower():
                    column_indices['Основная категория'] = i
        
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


# Global instance
finance_service = FinanceService()
