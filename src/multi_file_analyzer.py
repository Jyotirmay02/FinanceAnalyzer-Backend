#!/usr/bin/env python3
"""
Multi-file Financial Analyzer
Process multiple bank statement files together for comprehensive analysis
"""

import pandas as pd
import glob
from pathlib import Path
import sys
import os

from data_loader import DataLoader
from transaction_processor import TransactionProcessor
from excel_writer import ExcelWriter
from finance_analyzer import FinanceAnalyzer

def detect_bank_format(file_path):
    """Detect bank format by examining file content"""
    try:
        # Read first few lines to detect format
        with open(file_path, 'r', encoding='utf-8') as f:
            first_lines = [f.readline().strip() for _ in range(30)]
        
        content = '\n'.join(first_lines)
        
        if 'Account Name' in content and 'SBI' in content.upper():
            return 'SBI'
        elif 'Current & Saving Account Statement' in content or 'CANARA' in content.upper():
            return 'CANARA'
        else:
            return 'UNKNOWN'
    except:
        return 'UNKNOWN'

def load_bank_file(file_path):
    """Load bank file based on detected format"""
    bank_format = detect_bank_format(file_path)
    print(f"  🏦 Detected format: {bank_format}")
    
    if bank_format == 'SBI':
        # SBI format: tab-separated, skip 20 rows
        df = pd.read_csv(file_path, sep='\t', skiprows=20, encoding='utf-8')
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Rename SBI columns
        df = df.rename(columns={
            'Debit': 'Debit (₹)',
            'Credit': 'Credit (₹)'
        })
        
    elif bank_format == 'CANARA':
        # Canara format: CSV, find header row
        df = pd.read_csv(file_path, skiprows=26, encoding='utf-8')
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        
        # Rename Canara columns to match standard format
        df = df.rename(columns={
            'Debit': 'Debit (₹)',
            'Credit': 'Credit (₹)'
        })
        
    else:
        raise ValueError(f"Unsupported bank format: {bank_format}")
    
    # Clean and convert numeric columns
    for col in ['Debit (₹)', 'Credit (₹)']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('=', '').str.replace('"', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df, bank_format
    """
    Process multiple bank statement files and combine them for analysis
    
    Args:
        input_files: List of input files to process
        output_filename: Name for the combined analysis output
    """
    
def process_multiple_files(input_files, output_filename="multi_year_analysis.xlsx"):
    """
    Process multiple bank statement files and combine them for analysis
    
    Args:
        input_files: List of input files to process
        output_filename: Name for the combined analysis output
    """
    
    files = input_files
    if not files:
        print(f"❌ No files provided")
        return None
    
    files.sort()  # Sort files for consistent processing
    print(f"🔍 Found {len(files)} files to process:")
    for file in files:
        print(f"  - {file}")
    
    all_transactions = []
    
    # Process each file
    for file_path in files:
        print(f"\n📊 Processing {file_path}...")
        try:
            # Create analyzer and use its normal flow for proper categorization
            analyzer = FinanceAnalyzer(file_path)
            
            # Load data using analyzer's method
            analyzer.load_data()
            
            # Process transactions for categorization
            analyzer.process_transactions()
            
            # Get the categorized data
            processed_df = analyzer.categorized_df.copy()
            
            print(f"  ✅ Loaded and categorized {len(processed_df)} transactions")
            
            # Add source file info
            processed_df['Source_File'] = Path(file_path).name
            processed_df['Bank'] = detect_bank_format(file_path)
            
            all_transactions.append(processed_df)
            
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
            continue
    
    if not all_transactions:
        print("❌ No transactions were successfully loaded")
        return None
    
    # Combine all transactions
    print(f"\n🔄 Combining all transactions...")
    combined_df = pd.concat(all_transactions, ignore_index=True)
    
    # Sort by date
    combined_df['Txn Date'] = pd.to_datetime(combined_df['Txn Date'], errors='coerce')
    combined_df = combined_df.sort_values('Txn Date')
    
    # Extract year from transaction date
    combined_df['Year'] = combined_df['Txn Date'].dt.year.astype(str)
    
    # Ensure Category column exists
    if 'Category' not in combined_df.columns:
        combined_df['Category'] = 'Uncategorized'
    
    print(f"✅ Combined {len(combined_df)} total transactions from {len(files)} files")
    
    # Generate comprehensive analysis
    print(f"\n📈 Generating comprehensive analysis...")
    
    # Create basic summaries for the writer
    # Handle different column name formats
    debit_col = 'Debit (₹)' if 'Debit (₹)' in combined_df.columns else 'Debit'
    credit_col = 'Credit (₹)' if 'Credit (₹)' in combined_df.columns else 'Credit'
    
    # Calculate counts
    debit_count = (combined_df[debit_col] > 0).sum()
    credit_count = (combined_df[credit_col] > 0).sum()
    
    overall_summary = {
        'total_transactions': len(combined_df),
        'total_debits': combined_df[debit_col].sum(),
        'total_credits': combined_df[credit_col].sum(),
        'debit_count': debit_count,
        'credit_count': credit_count,
        'date_range_start': combined_df['Txn Date'].min().strftime('%Y-%m-%d') if pd.notna(combined_df['Txn Date'].min()) else 'N/A',
        'date_range_end': combined_df['Txn Date'].max().strftime('%Y-%m-%d') if pd.notna(combined_df['Txn Date'].max()) else 'N/A',
        'report_generated_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Create category summary (use Category column instead of Description)
    if 'Category' in combined_df.columns:
        category_summary = combined_df.groupby('Category').agg({
            debit_col: 'sum',
            credit_col: 'sum'
        }).reset_index()
    else:
        # Fallback to Description if Category not available
        category_summary = combined_df.groupby('Description').agg({
            debit_col: 'sum',
            credit_col: 'sum'
        }).reset_index()
    
    # Output to visuals directory (handle both root and src execution)
    if Path("visuals").exists():
        # Running from root directory
        output_path = Path("visuals") / output_filename
    else:
        # Running from src directory
        output_path = Path("../visuals") / output_filename
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    writer = ExcelWriter(str(output_path))
    writer.write_analysis_report(combined_df, overall_summary, category_summary)
    
    # Print summary statistics
    print(f"\n📊 MULTI-YEAR SUMMARY:")
    print(f"   Total Transactions: {len(combined_df):,}")
    print(f"   Date Range: {combined_df['Txn Date'].min().strftime('%Y-%m-%d')} to {combined_df['Txn Date'].max().strftime('%Y-%m-%d')}")
    print(f"   Total Debits: ₹{combined_df[debit_col].sum():,.2f}")
    print(f"   Total Credits: ₹{combined_df[credit_col].sum():,.2f}")
    print(f"   Net Change: ₹{(combined_df[credit_col].sum() - combined_df[debit_col].sum()):,.2f}")
    
    # Year-wise summary
    print(f"\n📅 YEAR-WISE BREAKDOWN:")
    year_summary = combined_df.groupby('Year').agg({
        debit_col: 'sum',
        credit_col: 'sum',
        'Txn Date': 'count'
    }).round(2)
    year_summary['Net Change'] = year_summary[credit_col] - year_summary[debit_col]
    year_summary.columns = ['Total Debits (₹)', 'Total Credits (₹)', 'Transaction Count', 'Net Change (₹)']
    print(year_summary.to_string())
    
    print(f"\n✅ Multi-year analysis complete! Results saved to: {output_path}")
    return str(output_path)

def main():
    """Main function to run multi-file analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-file Financial Analyzer')
    parser.add_argument('--input', nargs='+', required=True, 
                       help='Input files to process (e.g., --input data/SBI_2022.xls data/SBI_2023.xls)')
    parser.add_argument('--output', default='multi_year_sbi_analysis.xlsx',
                       help='Output filename (default: multi_year_sbi_analysis.xlsx)')
    
    args = parser.parse_args()
    
    # Handle paths correctly whether running from root or src directory
    input_files = []
    for file in args.input:
        if Path(file).exists():
            # File exists as specified
            input_files.append(file)
        elif Path(f"../{file}").exists():
            # Try with ../ prefix (running from src)
            input_files.append(f"../{file}")
        elif file.startswith('data/') and Path(file).exists():
            # Running from root, file exists
            input_files.append(file)
        else:
            # Default: assume running from root
            input_files.append(file)
    
    print("🚀 Multi-File Financial Analyzer")
    print("=" * 50)
    
    result = process_multiple_files(input_files, args.output)
    
    if result:
        print(f"\n🎉 Analysis completed successfully!")
        print(f"📁 Output file: {result}")
    else:
        print(f"\n❌ Analysis failed!")

if __name__ == "__main__":
    main()
