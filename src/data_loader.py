import pandas as pd
from pathlib import Path
from typing import List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """Handles loading and reading transaction data from Excel and CSV files"""
    
    def __init__(self, file_path: str):
        """
        Initialize data loader
        
        Args:
            file_path: Path to Excel or CSV file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine file type
        self.file_extension = self.file_path.suffix.lower()
        self.is_csv = self.file_extension == '.csv'
        self.is_excel = self.file_extension in ['.xlsx', '.xls']
        
        # Check if .xls file is actually text format (common with SBI statements)
        if self.file_extension == '.xls':
            try:
                # Try to read as text first
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if 'Account Name' in first_line or first_line.startswith('Account'):
                        logger.info("Detected SBI text format in .xls file, treating as CSV")
                        self.is_csv = True
                        self.is_excel = False
            except:
                pass  # If reading as text fails, continue with Excel processing
        
        if not (self.is_csv or self.is_excel):
            raise ValueError(f"Unsupported file format: {self.file_extension}. Supported formats: .csv, .xlsx, .xls")
        
        # For CSV files, detect if it's a bank statement format
        self.is_bank_statement_csv = False
        if self.is_csv:
            self.is_bank_statement_csv = self._detect_bank_statement_format()
        
        logger.info(f"Initialized {'Bank Statement CSV' if self.is_bank_statement_csv else 'CSV' if self.is_csv else 'Excel'} data loader for: {file_path}")
    
    def _detect_bank_statement_format(self) -> bool:
        """Detect if CSV is in bank statement format by looking for 'Txn Date' header"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'Txn Date' in content and 'Account Statement' in content
        except Exception:
            return False
    
    def get_sheet_names(self) -> List[str]:
        """Get list of sheet names (Excel) or return default for CSV"""
        if self.is_csv:
            return ["default"]  # CSV files don't have sheets
        
        try:
            excel_file = pd.ExcelFile(self.file_path)
            return excel_file.sheet_names
        except Exception as e:
            logger.error(f"Error reading sheet names: {e}")
            raise
    
    def read_sheet_data(self, sheet_name: str = None, header_row: Optional[int] = None) -> pd.DataFrame:
        """
        Read data from specific sheet (Excel) or entire CSV file
        
        Args:
            sheet_name: Name of the sheet to read (ignored for CSV)
            header_row: Row number to use as header (0-indexed), None for no header
            
        Returns:
            DataFrame with data
        """
        try:
            if self.is_csv:
                # Check if it's SBI format (tab-separated)
                if self.file_extension == '.xls':
                    df = pd.read_csv(self.file_path, header=header_row, sep='\t')
                else:
                    df = pd.read_csv(self.file_path, header=header_row)
                logger.info(f"Successfully loaded CSV file with {len(df)} rows")
            else:
                df = pd.read_excel(
                    self.file_path, 
                    sheet_name=sheet_name,
                    header=header_row,
                    engine='xlrd' if self.file_extension == '.xls' else 'openpyxl'
                )
                logger.info(f"Successfully loaded sheet '{sheet_name}' with {len(df)} rows")
            
            return df
        except Exception as e:
            logger.error(f"Error reading data: {e}")
            raise
    
    def read_raw_data(self, sheet_name: str = None) -> List[List[Any]]:
        """
        Read raw data as list of lists (similar to original TypeScript)
        
        Args:
            sheet_name: Name of the sheet to read (ignored for CSV)
            
        Returns:
            List of lists containing raw cell values
        """
        try:
            if self.is_bank_statement_csv:
                # Use specialized bank statement reader
                from bank_statement_reader import read_bank_statement_csv
                return read_bank_statement_csv(str(self.file_path))
            elif self.is_csv:
                # Use standard CSV reading for simple CSV files
                if self.file_extension == '.xls':
                    # Handle SBI format manually due to inconsistent column structure
                    rows = []
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            # Split by tab and pad with empty strings to ensure consistent column count
                            parts = line.strip().split('\t')
                            # Pad to 9 columns to handle inconsistent structure
                            while len(parts) < 9:
                                parts.append('')
                            rows.append(parts)
                    df = pd.DataFrame(rows)
                else:
                    df = pd.read_csv(
                        self.file_path, 
                        header=None,
                        encoding='utf-8',
                        on_bad_lines='skip',
                        engine='python',
                        quoting=1,
                        skipinitialspace=True
                    )
                logger.info(f"Successfully loaded raw CSV data with {len(df)} rows")
                return df.values.tolist()
            else:
                df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=None, engine='xlrd' if self.file_extension == '.xls' else 'openpyxl')
                logger.info(f"Successfully loaded raw Excel data from sheet '{sheet_name}' with {len(df)} rows")
                return df.values.tolist()
            
        except Exception as e:
            logger.error(f"Error reading raw data: {e}")
            raise
    
    def validate_sheet_structure(self, data: List[List[Any]], expected_columns: int, 
                                data_start_row: int) -> bool:
        """
        Validate that the sheet has expected structure
        
        Args:
            data: Raw sheet data
            expected_columns: Expected number of columns
            data_start_row: Row where data starts
            
        Returns:
            True if structure is valid
        """
        if len(data) <= data_start_row:
            logger.error(f"File has insufficient rows. Expected data start at row {data_start_row}")
            return False
        
        if len(data[0]) < expected_columns:
            logger.error(f"File has insufficient columns. Expected {expected_columns}, got {len(data[0])}")
            return False
        
        return True


# Backward compatibility alias
ExcelDataLoader = DataLoader
