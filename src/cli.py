"""
Command Line Interface for FinanceAnalyzer

Usage:
    python cli.py --input data/bank_statement.xlsx --output analysis_report.xlsx
    python cli.py --input data/bank_statement.xlsx --sheet "Sheet1" --category "Food & Dining"
"""

import argparse
import sys
from pathlib import Path
from finance_analyzer import FinanceAnalyzer


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Analyze financial transactions from Excel files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis (Excel)
  python cli.py --input data/bank_statement.xlsx
  
  # Basic analysis (CSV)
  python cli.py --input data/bank_statement.csv
  
  # Specify output file and sheet (Excel only)
  python cli.py --input data/bank_statement.xlsx --output my_analysis.xlsx --sheet "1754113304898"
  
  # Filter by category
  python cli.py --input data/bank_statement.csv --category "Food & Dining"
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to input Excel (.xlsx, .xls) or CSV (.csv) file'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='financial_analysis.xlsx',
        help='Output filename (default: financial_analysis.xlsx)'
    )
    
    parser.add_argument(
        '--sheet', '-s',
        help='Sheet name to analyze (Excel only, ignored for CSV files)'
    )
    
    parser.add_argument(
        '--category', '-c',
        help='Filter results by specific category'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for filtering (YYYY-MM-DD or DD-MM-YYYY)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for filtering (YYYY-MM-DD or DD-MM-YYYY)'
    )
    
    parser.add_argument(
        '--from',
        dest='from_date',
        help='Start date in MM-YYYY format (e.g., "11-2023")'
    )
    
    parser.add_argument(
        '--to',
        dest='to_date', 
        help='End date in MM-YYYY format (e.g., "08-2025")'
    )
    
    parser.add_argument(
        '--list-sheets',
        action='store_true',
        help='List available sheets in the Excel file'
    )
    
    parser.add_argument(
        '--output-dir',
        default='visuals',
        help='Output directory (default: visuals)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Display filter information
    if args.from_date or args.to_date:
        filter_desc = f"From: {args.from_date or 'Start'} To: {args.to_date or 'End'}"
        print(f"🔍 Date Range Filter: {filter_desc}")
    
    try:
        # Initialize analyzer
        print(f"🚀 Initializing FinanceAnalyzer with {args.input}")
        analyzer = FinanceAnalyzer(
            args.input, 
            output_dir=args.output_dir,
            from_date=args.from_date,
            to_date=args.to_date
        )
        
        # List sheets if requested
        if args.list_sheets:
            print("\n📊 Available sheets:")
            sheets = analyzer.get_available_sheets()
            for i, sheet in enumerate(sheets, 1):
                print(f"  {i}. {sheet}")
            return
        
        # Run analysis with filters
        if args.start_date or args.end_date:
            print(f"🔄 Analyzing with date filter: {args.start_date} to {args.end_date}")
            output_file = analyzer.analyze_with_date_filter(args.start_date, args.end_date)
        elif analyzer.data_loader.is_csv:
            print("🔄 Analyzing CSV file")
            # Extract just the filename for the analyzer
            output_filename = Path(args.output).name
            output_file = analyzer.run_full_analysis(output_filename=output_filename)
        else:
            sheet_to_analyze = args.sheet or '1754113304898'  # Default Excel sheet
            print(f"🔄 Analyzing Excel sheet: {sheet_to_analyze}")
            # Extract just the filename for the analyzer
            output_filename = Path(args.output).name
            output_file = analyzer.run_full_analysis(
                sheet_name=sheet_to_analyze,
                output_filename=output_filename
            )
        
        # Handle category filtering
        if args.category:
            print(f"\n🔍 Filtering by category: {args.category}")
            category_transactions = analyzer.get_category_transactions(args.category)
            
            if not category_transactions.empty:
                print(f"Found {len(category_transactions)} transactions in '{args.category}' category")
                
                # Save category-specific results
                category_filename = f"{args.category.replace(' ', '_').lower()}_transactions.xlsx"
                category_path = Path(args.output_dir) / category_filename
                category_transactions.to_excel(category_path, index=False)
                print(f"Category results saved to: {category_path}")
            else:
                print(f"No transactions found for category: {args.category}")
        
        print(f"\n✅ Analysis complete! Main results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
