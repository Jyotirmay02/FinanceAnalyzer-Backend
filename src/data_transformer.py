"""
Data Transformer for API Contract Compliance
Transforms data between different formats to ensure API contract consistency
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

class DataTransformer:
    """Transforms data to match API contracts"""
    
    @staticmethod
    def convert_numpy_types(obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: DataTransformer.convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [DataTransformer.convert_numpy_types(item) for item in obj]
        return obj
    
    @staticmethod
    def transform_multi_file_summary_to_standard(multi_file_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform multi-file analyzer summary to standard FinanceAnalyzer format
        
        Multi-file format:
        {
            'total_transactions': int,
            'total_debits': float,
            'total_credits': float,
            'debit_count': int,
            'credit_count': int,
            'date_range_start': str,
            'date_range_end': str
        }
        
        Standard format (expected by frontend):
        {
            'Total Spends (Debits)': float,
            'Total Credits': float,
            'Net Change': float,
            'Total Transactions': int,
            'Debit Count': int,
            'Credit Count': int,
            'Date Range': str
        }
        """
        if not multi_file_summary:
            return None
            
        # Calculate net change
        net_change = multi_file_summary.get('total_credits', 0) - multi_file_summary.get('total_debits', 0)
        
        # Create date range string
        start_date = multi_file_summary.get('date_range_start', 'N/A')
        end_date = multi_file_summary.get('date_range_end', 'N/A')
        date_range = f"{start_date} to {end_date}"
        
        standard_summary = {
            'Total Spends (Debits)': float(multi_file_summary.get('total_debits', 0)),
            'Total Credits': float(multi_file_summary.get('total_credits', 0)),
            'Net Change': float(net_change),
            'Total Transactions': int(multi_file_summary.get('total_transactions', 0)),
            'Debit Count': int(multi_file_summary.get('debit_count', 0)),
            'Credit Count': int(multi_file_summary.get('credit_count', 0)),
            'Date Range': date_range
        }
        
        return DataTransformer.convert_numpy_types(standard_summary)
    
    @staticmethod
    def transform_multi_file_categories_to_standard(category_df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Transform multi-file category summary to standard format
        
        Returns list of category dictionaries for frontend consumption
        """
        if category_df is None or category_df.empty:
            return []
        
        categories = []
        for category in category_df.index:
            # Handle different column name formats
            debit_col = 'Debit (₹)' if 'Debit (₹)' in category_df.columns else 'Total Debit'
            credit_col = 'Credit (₹)' if 'Credit (₹)' in category_df.columns else 'Total Credit'
            count_col = 'Count' if 'Count' in category_df.columns else 'Transaction Count'
            
            category_data = {
                'Category': str(category),
                'Total Debit': float(category_df.loc[category, debit_col] if debit_col in category_df.columns else 0),
                'Total Credit': float(category_df.loc[category, credit_col] if credit_col in category_df.columns else 0),
                'Transaction Count': int(category_df.loc[category, count_col] if count_col in category_df.columns else 0)
            }
            categories.append(category_data)
        
        # Sort by Total Debit descending
        categories.sort(key=lambda x: x['Total Debit'], reverse=True)
        
        return DataTransformer.convert_numpy_types(categories)
    
    @staticmethod
    def create_mock_analyzer_from_multi_file(combined_df: pd.DataFrame, overall_summary: Dict[str, Any], category_summary: Optional[pd.DataFrame] = None):
        """
        Create a mock analyzer object that matches FinanceAnalyzer interface
        for multi-file results
        """
        class MockAnalyzer:
            def __init__(self, df, summary, categories):
                self.categorized_df = df
                self.raw_overall_summary = summary
                self.raw_category_summary = categories
                
                # Transform to standard format
                self.overall_summary = DataTransformer.transform_multi_file_summary_to_standard(summary)
                self.category_summary = categories
        
        return MockAnalyzer(combined_df, overall_summary, category_summary)
    
    @staticmethod
    def ensure_standard_format(analyzer) -> Dict[str, Any]:
        """
        Ensure analyzer data is in standard format expected by API endpoints
        """
        if not analyzer:
            return None
            
        # Check if it's already in standard format
        if hasattr(analyzer, 'overall_summary') and analyzer.overall_summary:
            if 'Total Spends (Debits)' in analyzer.overall_summary:
                # Already in standard format
                return analyzer.overall_summary
            else:
                # Needs transformation (multi-file format)
                return DataTransformer.transform_multi_file_summary_to_standard(analyzer.overall_summary)
        
        return None
