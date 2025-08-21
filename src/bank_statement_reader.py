"""
Specialized reader for bank statement CSV files with complex formatting
"""

import csv
import pandas as pd
from typing import List, Any
import logging

logger = logging.getLogger(__name__)


def read_bank_statement_csv(file_path: str) -> List[List[Any]]:
    """
    Read bank statement CSV with special handling for complex formatting
    
    Args:
        file_path: Path to the bank statement CSV file
        
    Returns:
        List of lists containing the parsed data
    """
    data = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read all lines
            lines = file.readlines()
            
            # Find the header line (contains "Txn Date")
            header_line_idx = None
            for i, line in enumerate(lines):
                if 'Txn Date' in line and 'Value Date' in line:
                    header_line_idx = i
                    break
            
            if header_line_idx is None:
                raise ValueError("Could not find transaction header line in CSV")
            
            logger.info(f"Found transaction header at line {header_line_idx + 1}")
            
            # Process lines starting from header
            csv_reader = csv.reader(lines[header_line_idx:], quotechar='"')
            
            for row_idx, row in enumerate(csv_reader):
                # Skip empty rows
                if not row or all(cell.strip() == '' for cell in row):
                    continue
                
                # Clean Excel-style formatting from each cell
                cleaned_row = []
                for cell in row:
                    cell = str(cell).strip()
                    # Remove Excel-style =" formatting
                    if cell.startswith('="') and cell.endswith('"'):
                        cell = cell[2:-1]
                    elif cell.startswith('=') and cell.endswith(''):
                        cell = cell[1:]
                    cleaned_row.append(cell)
                
                # Ensure we have at least 8 columns (pad with empty strings if needed)
                while len(cleaned_row) < 8:
                    cleaned_row.append('')
                
                # Take only first 8 columns to match expected format
                data.append(cleaned_row[:8])
            
            logger.info(f"Successfully parsed {len(data)} rows from bank statement CSV")
            return data
            
    except Exception as e:
        logger.error(f"Error reading bank statement CSV: {e}")
        raise


def clean_bank_statement_value(value: str) -> str:
    """Clean bank statement CSV values"""
    if not value:
        return ""
    
    value = str(value).strip()
    
    # Remove Excel-style formatting
    if value.startswith('="') and value.endswith('"'):
        return value[2:-1]
    elif value.startswith('='):
        return value[1:]
    
    return value
