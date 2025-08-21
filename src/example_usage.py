#!/usr/bin/env python3
"""
Example usage of the FinanceAnalyzer with optional time filtering

Usage:
    python src/example_usage.py                           # Analyze all data
    python src/example_usage.py --year 2022              # Filter by year
    python src/example_usage.py --month 9                # Filter by month (across all years)  
    python src/example_usage.py --year 2022 --month 9    # Filter by specific year-month
    python src/example_usage.py --from 09-2023           # Filter from Sep 2023 onwards
    python src/example_usage.py --to 08-2025             # Filter up to Aug 2025
    python src/example_usage.py --from 09-2023 --to 08-2025  # Filter date range
"""

import sys
import argparse
from pathlib import Path

from finance_analyzer import FinanceAnalyzer


def main():
    """Main function with command line argument support"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Analyze financial transactions with optional time filtering')
    parser.add_argument('--year', type=int, help='Filter by year (e.g., 2022)')
    parser.add_argument('--month', type=int, choices=range(1, 13), help='Filter by month (1-12)')
    parser.add_argument('--from', dest='from_date', help='Start date in MM-YYYY format (e.g., "09-2023")')
    parser.add_argument('--to', dest='to_date', help='End date in MM-YYYY format (e.g., "08-2025")')
    parser.add_argument('--input', default='data/bank_statement.csv', help='Input file path')
    
    args = parser.parse_args()
    
    # Display filter information
    if args.from_date or args.to_date:
        filter_desc = f"From: {args.from_date or 'Start'} To: {args.to_date or 'End'}"
        print(f"🔍 Date Range Filter: {filter_desc}")
        print()
    elif args.year or args.month:
        filter_desc = f"Year: {args.year or 'All'}, Month: {args.month or 'All'}"
        print(f"🔍 Time Filter Applied: {filter_desc}")
        print()
    
    # Find input file
    input_file = Path(args.input)
    
    if not input_file.exists():
        # Try different locations
        possible_paths = [
            Path("data/bank_statement.csv"),
            Path("../data/bank_statement.csv"),
            Path("data/sample_transactions.xlsx"),
            Path("../data/sample_transactions.xlsx")
        ]
        
        for path in possible_paths:
            if path.exists():
                input_file = path
                break
        else:
            print("❌ No input file found. Please ensure you have:")
            print("   - data/bank_statement.csv, or")
            print("   - data/sample_transactions.xlsx")
            return
    
    print(f"📄 Found input file: {input_file}")
    
    # Initialize analyzer with time filtering
    print("🚀 Initializing FinanceAnalyzer...")
    analyzer = FinanceAnalyzer(
        str(input_file), 
        year_filter=args.year,
        month_filter=args.month,
        from_date=args.from_date,
        to_date=args.to_date
    )
    
    # Detect file type
    if input_file.suffix.lower() == '.csv':
        print("📁 File type detected: CSV")
    else:
        print("📁 File type detected: Excel")
    
    print()
    
    # Run analysis
    if input_file.suffix.lower() == '.csv':
        print("🔄 Running full analysis on CSV file...")
        output_path = analyzer.run_full_analysis()
    else:
        print("🔄 Running full analysis on Excel file...")
        output_path = analyzer.run_full_analysis()
    
    print(f"\n✅ Analysis complete! Results saved to: {output_path}")
    
    # Show food transactions as example
    if analyzer.categorized_df is not None:
        food_transactions = analyzer.categorized_df[
            analyzer.categorized_df['Category'] == 'Food & Dining'
        ]
        
        print(f"\n🍕 Food & Dining transactions:")
        if len(food_transactions) > 0:
            print(f"Found {len(food_transactions)} food transactions")
            print(food_transactions[['Description', 'Debit', 'Category']].head())
        else:
            print("No food transactions found")


if __name__ == "__main__":
    main()
