"""
Main transaction processing and categorization logic
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime

from constants import ColumnKey, COLUMN_INDEX, CATEGORY_KEYWORDS, DEFAULT_DATA_START_ROW
from utils import parse_amount, get_category, safe_str, clean_cheque_number, clean_excel_csv_value
from upi_categorizer import get_upi_subcategory

logger = logging.getLogger(__name__)


class TransactionProcessor:
    """Processes and categorizes financial transactions"""
    
    def __init__(self, data_start_row: int = DEFAULT_DATA_START_ROW, 
                 category_keywords: Dict[str, str] = None):
        """
        Initialize transaction processor
        
        Args:
            data_start_row: Row number where transaction data starts (0-indexed)
            category_keywords: Custom category keywords mapping
        """
        self.data_start_row = data_start_row
        self.category_keywords = category_keywords or CATEGORY_KEYWORDS
    
    def process_transactions(self, raw_data: List[List[Any]]) -> pd.DataFrame:
        """
        Process raw transaction data and add categories
        
        Args:
            raw_data: Raw data from Excel sheet or CSV file
            
        Returns:
            DataFrame with processed and categorized transactions
        """
        # Check if this is SBI format
        if self._is_sbi_format(raw_data):
            return self._process_sbi_format(raw_data)
        
        # Default processing for other formats
        if len(raw_data) <= self.data_start_row:
            raise ValueError(f"Insufficient data rows. Expected data start at row {self.data_start_row}")
        
        # Get headers and add Category column
        headers = list(raw_data[self.data_start_row])
        
        # Handle NaN values in headers (common in CSV files)
        headers = [str(h) if h is not None and str(h) != 'nan' else f'Column_{i}' 
                  for i, h in enumerate(headers)]
        
        headers.append("Category")
        
        processed_rows = []
        
        # Process each transaction row
        for i in range(self.data_start_row + 1, len(raw_data)):
            row = raw_data[i]
            processed_row = self._format_transaction_row(row)
            processed_rows.append(processed_row)
        
        # Create DataFrame
        df = pd.DataFrame(processed_rows, columns=headers)
        logger.info(f"Processed {len(processed_rows)} transactions")
        
        return df
    
    def _format_transaction_row(self, row: List[Any]) -> List[Any]:
        """
        Format a single transaction row with proper data types and category
        
        Args:
            row: Raw transaction row data
            
        Returns:
            Formatted row with category
        """
        # Helper function to handle NaN values
        def safe_get(row, index, default=""):
            try:
                value = row[index] if index < len(row) else default
                # Handle pandas NaN values
                if pd.isna(value):
                    return default
                return value
            except (IndexError, TypeError):
                return default
        
        # Extract and format each column with Excel CSV cleaning
        txn_date = clean_excel_csv_value(safe_get(row, COLUMN_INDEX[ColumnKey.TXN_DATE]))
        value_date = clean_excel_csv_value(safe_get(row, COLUMN_INDEX[ColumnKey.VALUE_DATE]))
        cheque_no = clean_cheque_number(safe_get(row, COLUMN_INDEX[ColumnKey.CHEQUE_NO]))
        description = clean_excel_csv_value(safe_get(row, COLUMN_INDEX[ColumnKey.DESCRIPTION]))
        branch_code = clean_excel_csv_value(safe_get(row, COLUMN_INDEX[ColumnKey.BRANCH_CODE]))
        
        # Parse amounts (handle NaN values)
        debit = parse_amount(safe_get(row, COLUMN_INDEX[ColumnKey.DEBIT], 0))
        credit = parse_amount(safe_get(row, COLUMN_INDEX[ColumnKey.CREDIT], 0))
        balance = parse_amount(safe_get(row, COLUMN_INDEX[ColumnKey.BALANCE], 0))
        
        # Determine category - Check UPI first to avoid conflicts
        if "UPI/" in description.upper():
            # This is a UPI transaction, use UPI subcategorizer
            category = get_upi_subcategory(description)
        else:
            # Non-UPI transaction, use general categorization
            category = get_category(description, self.category_keywords)
            
            # If it's still categorized as UPI Transfer but not a UPI transaction, 
            # it might be a false positive
            if category == "UPI Transfer":
                category = "Others"
        
        return [
            txn_date,
            value_date,
            cheque_no,
            description,
            branch_code,
            debit,
            credit,
            balance,
            category
        ]
    
    def generate_overall_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate overall financial summary
        
        Args:
            df: Processed transactions DataFrame
            
        Returns:
            Dictionary with summary statistics
        """
        total_debit = df['Debit'].sum()
        total_credit = df['Credit'].sum()
        spend_count = (df['Debit'] > 0).sum()
        credit_count = (df['Credit'] > 0).sum()
        
        # Calculate net change (simplified version)
        net_change = total_credit - total_debit
        
        summary = {
            "Total Spends (Debits)": total_debit,
            "Total Credits": total_credit,
            "Net Change": net_change,
            "Number of Spend Transactions": spend_count,
            "Number of Credit Transactions": credit_count,
            "Generated At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info(f"Generated overall summary: Net change = {net_change}")
        return summary
    
    def _is_sbi_format(self, raw_data: List[List[Any]]) -> bool:
        """Check if the data is in SBI format"""
        if len(raw_data) < 5:
            return False
        
        # Check for SBI-specific header patterns
        header_text = ' '.join(str(cell) for row in raw_data[:15] for cell in row if cell)
        
        is_sbi = ('Account Name' in header_text and 
                  ('SBI' in header_text.upper() or 'State Bank' in header_text or 'Txn Date' in header_text))
        
        return is_sbi
    
    def _process_sbi_format(self, raw_data: List[List[Any]]) -> pd.DataFrame:
        """Process SBI bank statement format"""
        logger.info("Processing SBI format data")
        
        # Find where transaction data starts (look for header row with "Txn Date")
        transaction_start = 0
        for i, row in enumerate(raw_data):
            if len(row) > 0:
                row_text = ' '.join(str(cell) for cell in row if cell)
                if 'Txn Date' in row_text:
                    transaction_start = i + 1  # Data starts after header
                    break
        
        logger.info(f"Found transaction data starting at row {transaction_start}")
        
        # Process transaction rows
        processed_rows = []
        headers = ['Txn Date', 'Value Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance', 'Category']
        
        for i in range(transaction_start, len(raw_data)):
            row = raw_data[i]
            if len(row) < 7:
                continue
                
            # Skip footer rows
            if 'computer generated' in str(row).lower():
                break
                
            try:
                # Parse SBI format: Date, Value Date, Description, Reference, Debit, Credit, Balance
                txn_date = str(row[0]).strip()
                value_date = str(row[1]).strip()
                description = str(row[2]).strip()
                reference = str(row[3]).strip() if len(row) > 3 else ""
                debit_str = str(row[4]).strip() if len(row) > 4 else ""
                credit_str = str(row[5]).strip() if len(row) > 5 else ""
                balance_str = str(row[6]).strip() if len(row) > 6 else ""
                
                # Skip empty rows or invalid dates
                if not txn_date or txn_date == 'nan' or len(txn_date) < 5:
                    continue
                
                # Parse amounts
                debit = self._parse_amount(debit_str) if debit_str and debit_str != 'nan' else 0.0
                credit = self._parse_amount(credit_str) if credit_str and credit_str != 'nan' else 0.0
                balance = self._parse_amount(balance_str) if balance_str and balance_str != 'nan' else 0.0
                
                # Categorize transaction
                full_description = f"{description} {reference}".strip()
                
                # Use the same categorization logic as the original code
                if "UPI/" in full_description.upper():
                    category = get_upi_subcategory(full_description)
                else:
                    category = get_category(full_description, self.category_keywords)
                    if category == "UPI Transfer":
                        category = "Others"
                
                processed_row = [txn_date, value_date, full_description, reference, debit, credit, balance, category]
                processed_rows.append(processed_row)
                
            except Exception as e:
                logger.warning(f"Error processing SBI row {i}: {e}")
                continue
        
        if not processed_rows:
            raise ValueError("No valid transaction data found in SBI format")
        
        df = pd.DataFrame(processed_rows, columns=headers)
        logger.info(f"Successfully processed {len(df)} SBI transactions")
        return df
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string, handling commas and formatting"""
        if not amount_str or amount_str.strip() == '' or amount_str == 'nan':
            return 0.0
        
        # Remove commas and spaces
        clean_amount = amount_str.replace(',', '').replace(' ', '').strip()
        
        try:
            return float(clean_amount)
        except ValueError:
            return 0.0
    
    def generate_category_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate category-wise spending summary with UPI consolidation
        
        Args:
            df: Processed transactions DataFrame
            
        Returns:
            DataFrame with category summary (UPI subcategories consolidated)
        """
        # Group by category and calculate aggregations
        category_summary = df.groupby('Category').agg({
            'Debit': ['sum', 'count'],
            'Credit': ['sum', 'count']
        }).round(2)
        
        # Flatten column names
        category_summary.columns = [
            'Total Debit', 'Debit Count', 'Total Credit', 'Credit Count'
        ]
        
        # Reset index to make Category a column
        category_summary = category_summary.reset_index()
        
        # Consolidate UPI subcategories into single UPI category
        upi_rows = category_summary[category_summary['Category'].str.startswith('UPI-')]
        non_upi_rows = category_summary[~category_summary['Category'].str.startswith('UPI-')]
        
        if len(upi_rows) > 0:
            # Create consolidated UPI row
            upi_consolidated = pd.DataFrame({
                'Category': ['UPI'],
                'Total Debit': [upi_rows['Total Debit'].sum()],
                'Debit Count': [upi_rows['Debit Count'].sum()],
                'Total Credit': [upi_rows['Total Credit'].sum()],
                'Credit Count': [upi_rows['Credit Count'].sum()]
            })
            
            # Combine non-UPI rows with consolidated UPI
            category_summary = pd.concat([non_upi_rows, upi_consolidated], ignore_index=True)
        
        # Sort by Total Debit descending
        category_summary = category_summary.sort_values('Total Debit', ascending=False)
        
        logger.info(f"Generated category summary for {len(category_summary)} categories (UPI consolidated)")
        return category_summary
    
    def get_top_spending_categories(self, df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
        """
        Get top N spending categories
        
        Args:
            df: Processed transactions DataFrame
            top_n: Number of top categories to return
            
        Returns:
            DataFrame with top spending categories
        """
        category_summary = self.generate_category_summary(df)
        return category_summary.head(top_n)
    
    def filter_by_category(self, df: pd.DataFrame, category: str) -> pd.DataFrame:
        """
        Filter transactions by category
        
        Args:
            df: Processed transactions DataFrame
            category: Category to filter by
            
        Returns:
            Filtered DataFrame
        """
        filtered_df = df[df['Category'] == category].copy()
        logger.info(f"Filtered {len(filtered_df)} transactions for category '{category}'")
        return filtered_df
    
    def filter_by_date_range(self, df: pd.DataFrame, start_date: str = None, 
                           end_date: str = None) -> pd.DataFrame:
        """
        Filter transactions by date range
        
        Args:
            df: Processed transactions DataFrame
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Filtered DataFrame
        """
        filtered_df = df.copy()
        
        if start_date:
            # This would need proper date parsing implementation
            logger.info(f"Date filtering not fully implemented yet")
        
        if end_date:
            # This would need proper date parsing implementation
            logger.info(f"Date filtering not fully implemented yet")
        
        return filtered_df
