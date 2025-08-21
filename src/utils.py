"""
Utility functions for data processing and formatting
"""

import re
from datetime import datetime
from typing import Any, Union


def parse_amount(value: Any) -> float:
    """
    Parse amount from various formats and return as float
    
    Args:
        value: Input value (string, number, etc.)
        
    Returns:
        Parsed amount as float, 0 if parsing fails
    """
    if value is None:
        return 0.0
    
    # Clean Excel-style CSV formatting first
    str_value = clean_excel_csv_value(value).strip()
    
    if not str_value:
        return 0.0
    
    is_negative = str_value.startswith("-")
    
    # Remove all non-numeric characters except decimal point
    cleaned = re.sub(r'[^0-9.]', '', str_value)
    
    # Find the first valid number pattern
    match = re.search(r'\d+(\.\d+)?', cleaned)
    if match:
        try:
            num = float(match.group(0))
            return -num if is_negative else num
        except ValueError:
            return 0.0
    
    return 0.0


def get_category(description: str, category_keywords: dict) -> str:
    """
    Categorize transaction based on description keywords
    
    Args:
        description: Transaction description
        category_keywords: Dictionary mapping keywords to categories
        
    Returns:
        Category name or "Others" if no match found
    """
    if not description:
        return "Others"
    
    lower_desc = description.lower()
    
    # Sort keywords by length descending for more specific matches first
    sorted_keywords = sorted(category_keywords.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword.lower() in lower_desc:
            return category_keywords[keyword]
    
    return "Others"


def format_date_time(date: datetime) -> str:
    """Format datetime as DD-MM-YYYY HH:MM:SS"""
    return date.strftime("%d-%m-%Y %H:%M:%S")


def format_date(date: datetime) -> str:
    """Format date as DD-MM-YYYY"""
    return date.strftime("%d-%m-%Y")


def safe_str(value: Any) -> str:
    """Safely convert value to string, handling None and empty values"""
    return str(value) if value is not None else ""


def clean_excel_csv_value(value: Any) -> str:
    """
    Clean Excel-style CSV values that start with =" and end with "
    
    Args:
        value: Input value that might be Excel-formatted
        
    Returns:
        Cleaned string value
    """
    if value is None:
        return ""
    
    str_value = str(value).strip()
    
    # Handle Excel-style formatting: ="value"
    if str_value.startswith('="') and str_value.endswith('"'):
        return str_value[2:-1]  # Remove =" from start and " from end
    
    return str_value


def clean_cheque_number(value: Any) -> str:
    """Clean and format cheque number"""
    cleaned = clean_excel_csv_value(value)
    return cleaned.strip() if cleaned else ""
