"""
Main FinanceAnalyzer class that orchestrates the entire analysis process
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from data_loader import DataLoader
from transaction_processor import TransactionProcessor
from excel_writer import ExcelWriter
from constants import DEFAULT_SHEET_NAME, DEFAULT_DATA_START_ROW, CSV_DATA_START_ROW, BANK_STATEMENT_CSV_DATA_START_ROW

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinanceAnalyzer:
    """
    Main class for analyzing financial transactions
    
    This class orchestrates the entire process:
    1. Load data from Excel files
    2. Process and categorize transactions
    3. Generate summaries and insights
    4. Export results
    """
    
    def __init__(self, input_file: str, output_dir: str = "visuals", year_filter: int = None, month_filter: int = None, from_date: str = None, to_date: str = None):
        """
        Initialize FinanceAnalyzer with optional time filtering
        
        Args:
            input_file: Path to input Excel or CSV file
            output_dir: Directory for output files (relative to project root)
            year_filter: Optional year to filter (e.g., 2022)
            month_filter: Optional month to filter (1-12)
            from_date: Optional start date in MM-YYYY format (e.g., "09-2023")
            to_date: Optional end date in MM-YYYY format (e.g., "08-2025")
        """
        self.input_file = Path(input_file)
        self.year_filter = year_filter
        self.month_filter = month_filter
        self.from_date = from_date
        self.to_date = to_date
        
        # Ensure output_dir is relative to the project root, not src/
        if output_dir.startswith("../"):
            # Remove ../ prefix to make it relative to current working directory
            output_dir = output_dir[3:]
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Log time filter if applied
        if year_filter or month_filter:
            filter_desc = f"Year: {year_filter or 'All'}, Month: {month_filter or 'All'}"
            logger.info(f"Time filter applied: {filter_desc}")
        elif from_date or to_date:
            filter_desc = f"From: {from_date or 'Start'}, To: {to_date or 'End'}"
            logger.info(f"Date range filter applied: {filter_desc}")
        
        # Initialize components
        self.data_loader = DataLoader(str(self.input_file))
        
        # Set data start row based on file type
        if self.data_loader.is_bank_statement_csv:
            data_start_row = BANK_STATEMENT_CSV_DATA_START_ROW
        elif self.data_loader.is_csv:
            data_start_row = CSV_DATA_START_ROW
        else:
            data_start_row = DEFAULT_DATA_START_ROW
            
        self.processor = TransactionProcessor(data_start_row=data_start_row)
        
        # Data storage
        self.raw_data = None
        self.categorized_df = None
        self.overall_summary = None
        self.category_summary = None
        
        logger.info(f"FinanceAnalyzer initialized with input: {self.input_file}")
    
    def load_data(self, sheet_name: str = None) -> None:
        """
        Load transaction data from Excel or CSV file
        
        Args:
            sheet_name: Name of the sheet to load (ignored for CSV files)
        """
        try:
            # Use default sheet name for Excel files, ignore for CSV
            if self.data_loader.is_csv:
                logger.info("Loading data from CSV file")
                self.raw_data = self.data_loader.read_raw_data()
            else:
                sheet_to_load = sheet_name or DEFAULT_SHEET_NAME
                logger.info(f"Loading data from Excel sheet: {sheet_to_load}")
                self.raw_data = self.data_loader.read_raw_data(sheet_to_load)
            
            logger.info(f"Loaded {len(self.raw_data)} rows of raw data")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise
    
    def process_transactions(self) -> pd.DataFrame:
        """
        Process and categorize transactions
        
        Returns:
            DataFrame with categorized transactions
        """
        if self.raw_data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        try:
            logger.info("Processing transactions...")
            self.categorized_df = self.processor.process_transactions(self.raw_data)
            logger.info(f"Successfully processed {len(self.categorized_df)} transactions")
            return self.categorized_df
        except Exception as e:
            logger.error(f"Failed to process transactions: {e}")
            raise
    
    def generate_summaries(self) -> Dict[str, Any]:
        """
        Generate overall and category summaries
        
        Returns:
            Dictionary containing both summaries
        """
        if self.categorized_df is None:
            raise ValueError("No processed data. Call process_transactions() first.")
        
        try:
            logger.info("Generating summaries...")
            
            # Generate overall summary
            self.overall_summary = self.processor.generate_overall_summary(self.categorized_df)
            
            # Generate category summary
            self.category_summary = self.processor.generate_category_summary(self.categorized_df)
            
            summaries = {
                'overall': self.overall_summary,
                'category': self.category_summary
            }
            
            logger.info("Summaries generated successfully")
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to generate summaries: {e}")
            raise
    
    def export_results(self, filename: str = "financial_analysis.xlsx") -> str:
        """
        Export analysis results to Excel file
        
        Args:
            filename: Name of output file
            
        Returns:
            Path to exported file
        """
        if any(x is None for x in [self.categorized_df, self.overall_summary, self.category_summary]):
            raise ValueError("Analysis not complete. Run full analysis first.")
        
        try:
            output_path = self.output_dir / filename
            writer = ExcelWriter(str(output_path))
            
            logger.info(f"Exporting results to {output_path}")
            writer.write_analysis_report(
                self.categorized_df,
                self.overall_summary,
                self.category_summary
            )
            
            logger.info(f"Results exported successfully to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to export results: {e}")
            raise
    
    def run_full_analysis(self, sheet_name: str = None, 
                         output_filename: str = "financial_analysis.xlsx") -> str:
        """
        Run complete analysis pipeline
        
        Args:
            sheet_name: Name of Excel sheet to analyze (ignored for CSV)
            output_filename: Name of output file
            
        Returns:
            Path to exported results file
        """
        try:
            logger.info("Starting full financial analysis...")
            
            # Step 1: Load data
            self.load_data(sheet_name)
            
            # Step 1.5: Apply time filtering if specified
            if self.year_filter or self.month_filter or self.from_date or self.to_date:
                self._apply_time_filter()
            
            # Step 2: Process transactions
            self.process_transactions()
            
            # Step 3: Generate summaries
            self.generate_summaries()
            
            # Step 4: Export results
            output_path = self.export_results(output_filename)
            
            logger.info("Full analysis completed successfully!")
            self.print_summary()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    def _apply_time_filter(self) -> None:
        """
        Apply year/month or date range filtering to loaded data
        """
        if self.raw_data is None or len(self.raw_data) == 0:
            logger.warning("No data to filter")
            return
        
        original_count = len(self.raw_data)
        
        try:
            # Parse dates from the data
            df = pd.DataFrame(self.raw_data[1:], columns=self.raw_data[0])  # Skip header
            
            # Handle different date formats
            try:
                df['ParsedDate'] = pd.to_datetime(df['Txn Date'], format='mixed', dayfirst=True)
            except:
                # Fallback for different date formats
                df['ParsedDate'] = pd.to_datetime(df['Txn Date'], errors='coerce')
            
            # Apply filters
            mask = pd.Series([True] * len(df))
            
            # Date range filtering (takes precedence over year/month)
            if self.from_date or self.to_date:
                if self.from_date:
                    try:
                        from_month, from_year = map(int, self.from_date.split('-'))
                        from_start = pd.Timestamp(year=from_year, month=from_month, day=1)
                        mask = mask & (df['ParsedDate'] >= from_start)
                    except:
                        logger.warning(f"Invalid from_date format: {self.from_date}")
                
                if self.to_date:
                    try:
                        to_month, to_year = map(int, self.to_date.split('-'))
                        # End of month
                        if to_month == 12:
                            to_end = pd.Timestamp(year=to_year + 1, month=1, day=1) - pd.Timedelta(days=1)
                        else:
                            to_end = pd.Timestamp(year=to_year, month=to_month + 1, day=1) - pd.Timedelta(days=1)
                        mask = mask & (df['ParsedDate'] <= to_end)
                    except:
                        logger.warning(f"Invalid to_date format: {self.to_date}")
            
            # Year/Month filtering (if no date range specified)
            elif self.year_filter or self.month_filter:
                if self.year_filter:
                    year_mask = df['ParsedDate'].dt.year == self.year_filter
                    mask = mask & year_mask
                    
                if self.month_filter:
                    month_mask = df['ParsedDate'].dt.month == self.month_filter
                    mask = mask & month_mask
            
            # Filter the data
            filtered_df = df[mask]
            
            # Convert back to raw_data format (header + rows)
            if len(filtered_df) > 0:
                self.raw_data = [self.raw_data[0]] + filtered_df.drop(['ParsedDate'], axis=1).values.tolist()
            else:
                # Keep header but no data rows
                self.raw_data = [self.raw_data[0]]
            
            filtered_count = len(self.raw_data) - 1  # Subtract header
            
            # Log filter details
            if self.from_date or self.to_date:
                filter_desc = f"From: {self.from_date or 'Start'}, To: {self.to_date or 'End'}"
            else:
                filter_desc = f"Year: {self.year_filter or 'All'}, Month: {self.month_filter or 'All'}"
            
            logger.info(f"Time filter applied: {filter_desc}")
            logger.info(f"Transactions: {original_count} → {filtered_count} (filtered {original_count - filtered_count})")
            
        except Exception as e:
            logger.error(f"Error applying time filter: {e}")
            logger.warning("Continuing with unfiltered data")

    def analyze_with_date_filter(self, start_date: str = None, end_date: str = None) -> str:
        """
        Run analysis with date filtering
        
        Args:
            start_date: Start date (YYYY-MM-DD or DD-MM-YYYY)
            end_date: End date (YYYY-MM-DD or DD-MM-YYYY)
            
        Returns:
            Path to output file
        """
        logger.info(f"Starting date-filtered analysis from {start_date} to {end_date}")
        
        try:
            # Load and process data
            raw_data = self.data_loader.read_raw_data()
            logger.info(f"Loaded {len(raw_data)} rows of raw data")
            
            # Process transactions
            logger.info("Processing transactions...")
            processed_df = self.processor.process_transactions(raw_data)
            logger.info(f"Successfully processed {len(processed_df)} transactions")
            
            # Apply date filtering
            if start_date or end_date:
                processed_df = self._filter_by_date(processed_df, start_date, end_date)
                logger.info(f"After date filtering: {len(processed_df)} transactions")
            
            # Store processed data
            self.processed_transactions = processed_df
            
            # Generate summaries
            logger.info("Generating summaries...")
            self.overall_summary = self.processor.generate_overall_summary(processed_df)
            self.category_summary = self.processor.generate_category_summary(processed_df)
            logger.info("Summaries generated successfully")
            
            # Export results
            output_path = self.output_dir / "date_filtered_analysis.xlsx"
            logger.info(f"Exporting results to {output_path}")
            
            writer = ExcelWriter(str(output_path))
            writer.write_analysis_report(processed_df, self.overall_summary, self.category_summary)
            
            logger.info("Date-filtered analysis completed successfully!")
            self.print_summary()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Date-filtered analysis failed: {e}")
            raise
    
    def _filter_by_date(self, df: pd.DataFrame, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Filter DataFrame by date range"""
        import pandas as pd
        
        # Convert Txn Date to datetime
        df['Date_Parsed'] = pd.to_datetime(df['Txn Date'], errors='coerce', dayfirst=True)
        
        if start_date:
            try:
                start_dt = pd.to_datetime(start_date, dayfirst=True)
                df = df[df['Date_Parsed'] >= start_dt]
                logger.info(f"Filtered from {start_date}: {len(df)} transactions remaining")
            except:
                logger.warning(f"Could not parse start date: {start_date}")
        
        if end_date:
            try:
                end_dt = pd.to_datetime(end_date, dayfirst=True)
                df = df[df['Date_Parsed'] <= end_dt]
                logger.info(f"Filtered to {end_date}: {len(df)} transactions remaining")
            except:
                logger.warning(f"Could not parse end date: {end_date}")
        
        return df.drop('Date_Parsed', axis=1)
    
    def print_summary(self) -> None:
        """Print a quick summary to console with filter information"""
        if self.overall_summary and self.category_summary is not None:
            print("\n" + "="*50)
            print("FINANCIAL ANALYSIS SUMMARY")
            print("="*50)
            
            # Add filter information
            if self.from_date or self.to_date:
                filter_desc = f"Date Range: {self.from_date or 'Start'} to {self.to_date or 'End'}"
                print(f"Filter Applied: {filter_desc}")
            elif self.year_filter or self.month_filter:
                filter_desc = f"Year: {self.year_filter or 'All'}, Month: {self.month_filter or 'All'}"
                print(f"Filter Applied: {filter_desc}")
            else:
                print("Filter Applied: All Data")
            print()
            
            print(f"Total Spends: ₹{self.overall_summary['Total Spends (Debits)']:,.2f}")
            print(f"Total Credits: ₹{self.overall_summary['Total Credits']:,.2f}")
            print(f"Net Change: ₹{self.overall_summary['Net Change']:,.2f}")
            print(f"Total Transactions: {self.overall_summary['Number of Spend Transactions'] + self.overall_summary['Number of Credit Transactions']}")
            
            print(f"\nTop 5 Spending Categories:")
            top_categories = self.category_summary.head(5)
            for _, row in top_categories.iterrows():
                print(f"  {row['Category']}: ₹{row['Total Debit']:,.2f}")
            
            print("="*50)
    
    def get_category_transactions(self, category: str) -> pd.DataFrame:
        """
        Get all transactions for a specific category
        
        Args:
            category: Category name
            
        Returns:
            Filtered DataFrame
        """
        if self.categorized_df is None:
            raise ValueError("No processed data available")
        
        return self.processor.filter_by_category(self.categorized_df, category)
    
    def get_available_sheets(self) -> list:
        """Get list of available sheets in the input file"""
        return self.data_loader.get_sheet_names()
