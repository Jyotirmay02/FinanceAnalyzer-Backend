#!/usr/bin/env python3
"""
Portfolio Financial Analyzer
Multi-bank portfolio analysis with self-transfer cancellation and broad categorization
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

# Comprehensive Broad Category Mapping
BROAD_CATEGORIES = {
    # Income & Salary
    "Salary": "Income & Salary",
    "SALARY": "Income & Salary", 
    "Amazon - Reimbursement": "Income & Salary",
    "Refunds": "Income & Salary",
    "UPI-Cashbacks-Cashback": "Income & Salary",
    "CREDIT INTEREST": "Income & Salary",
    
    # Self Transfers (to be cancelled)
    "Self Transfer": "Self Transfer",
    "Self Transfer - SBI": "Self Transfer",
    "Self Transfer - Canara": "Self Transfer", 
    "Self Transfer - Kotak": "Self Transfer",
    "Self Canara": "Self Transfer",
    "Self-Canara": "Self Transfer",
    "UPI-Friends-Self Transfer": "Self Transfer",
    
    # Food & Dining
    "UPI-Bills & Entertainment-Food & Dining": "Food & Dining",
    "UPI-Bills & Entertainment-Snacks": "Food & Dining",
    "UPI-Bills & Entertainment-Drinking Water": "Food & Dining",
    
    # Transportation & Commute
    "UPI-Travel-Daily Commute": "Transportation & Commute",
    "UPI-Travel-Cab Service": "Transportation & Commute",
    "UPI-Travel-Transport": "Transportation & Commute",
    "UPI-Travel-Bus Booking": "Transportation & Commute",
    "UPI-Travel-Train Booking": "Transportation & Commute",
    "Travel": "Transportation & Commute",
    
    # Utilities & Bills
    "UPI-Bills & Entertainment-Internet Bill": "Utilities & Bills",
    "UPI-Bills & Entertainment-Mobile Recharge": "Utilities & Bills",
    "UPI-Bills & Entertainment-Utilities": "Utilities & Bills",
    
    # Healthcare & Medical
    "UPI-Bills & Entertainment-Health-Med": "Healthcare & Medical",
    
    # Shopping & Retail
    "Shopping": "Shopping & Retail",
    "UPI-Shopping-E-commerce": "Shopping & Retail",
    "UPI-Shopping-Quick Commerce": "Shopping & Retail",
    "UPI-Shopping-Delivery": "Shopping & Retail",
    "UPI-Shopping-Apparels": "Shopping & Retail",
    "UPI-Shopping-Clothing": "Shopping & Retail",
    
    # Entertainment & Recreation
    "UPI-Bills & Entertainment-Entertainment": "Entertainment & Recreation",
    "UPI-Bills & Entertainment-Fitness": "Entertainment & Recreation",
    
    # Personal Care & Beauty
    "UPI-Bills & Entertainment-Salon": "Personal Care & Beauty",
    
    # Investment & SIP
    "Investment": "Investment & SIP",
    "UPI-Investment-Mutual Fund": "Investment & SIP",
    "UPI-Investment-NPS": "Investment & SIP",
    "UPI-Investment-Aadhaar": "Investment & SIP",
    "APY": "Investment & SIP",
    
    # Insurance & PMSBY
    "PMSBY": "Insurance & PMSBY",
    
    # Bank Charges & Fees (separated)
    "Bank Charges": "Bank Charges & Fees",
    
    # Cheq (separate category)
    "Cheq": "Cheq",
    "UPI-Credit Card Payment-Cheq": "Cheq",
    
    # ATM Withdrawals (separate category)
    "ATM Withdrawal": "ATM Withdrawals",
    
    # Credit Card Payments (separate category)
    "UPI-Credit Card Payment-Cheq": "Credit Card Payments",
    "UPI-Credit Card Payment-CRED": "Credit Card Payments",
    "Credit Card Payment": "Credit Card Payments",
    
    # Construction (all subcategories)
    "Cement": "Construction",
    "UPI-Construction-Cement": "Construction",
    "UPI-Construction-Brick": "Construction",
    "UPI-Construction-Sand": "Construction",
    "UPI-Construction-Wood": "Construction",
    "UPI-Construction-Chips": "Construction",
    "UPI-Construction-Contractor": "Construction",
    "UPI-Construction-Architect": "Construction",
    "UPI-Construction-Electrician": "Construction",
    "UPI-Construction-Plumbing": "Construction",
    "UPI-Construction-Electric Appliance": "Construction",
    "UPI-Construction-Grill": "Construction",
    "UPI-Construction-Gangadhar Hardware": "Construction",
    "Gangadhar Hardware": "Construction",
    "UPI-Construction-Construction UNKNOWN": "Construction",
    "UPI-Construction-Home Loan": "Construction",
    "UPI-Construction-Plot Purchase": "Construction",
    "UPI-Construction-Plot Purchase - TDS": "Construction",
    "Home Plan": "Construction",
    
    # Broker
    "Mantu-Plot": "Broker",
    
    # Donations & Temple (removed Bhagabat)
    "Donation": "Donations & Temple",
    "UPI-Bills & Entertainment-Donation": "Donations & Temple",
    
    # Travel & Vacation
    "UPI-Travel-AirTravel": "Travel & Vacation",
    
    # Rent & Housing
    "UPI-Rent & Housing-Rent": "Rent & Housing",
    "UPI-Rent & Housing-Flat Advance": "Rent & Housing",
    "UPI-Rent & Housing-Flat Expense": "Rent & Housing",
    
    # Friends & Family (Personal Transfers)
    "Dad": "Friends & Family",
    "Mommy": "Friends & Family",
    "Rabindra": "Friends & Family",
    "UPI-Friends-Abinash": "Friends & Family",
    "UPI-Friends-Arunanshu": "Friends & Family",
    "UPI-Friends-Ashwani": "Friends & Family",
    "UPI-Friends-Atul": "Friends & Family",
    "UPI-Friends-Ayush Amazon": "Friends & Family",
    "UPI-Friends-Ayushi Rastogi": "Friends & Family",
    "UPI-Friends-Bhajan": "Friends & Family",
    "UPI-Friends-Bishnu": "Friends & Family",
    "UPI-Friends-Biswajit": "Friends & Family",
    "UPI-Friends-Debabrat": "Friends & Family",
    "UPI-Friends-Dhruv": "Friends & Family",
    "UPI-Friends-Kalandi": "Friends & Family",
    "UPI-Friends-Lalit": "Friends & Family",
    "UPI-Friends-Madhur": "Friends & Family",
    "UPI-Friends-Maheswar": "Friends & Family",
    "UPI-Friends-Manjeet": "Friends & Family",
    "UPI-Friends-Md Altaf": "Friends & Family",
    "UPI-Friends-Mommy - (Piku apa)": "Friends & Family",
    "UPI-Friends-Pallove": "Friends & Family",
    "UPI-Friends-Parshu": "Friends & Family",
    "UPI-Friends-Pintu": "Friends & Family",
    "UPI-Friends-Prayag Shooken": "Friends & Family",
    "UPI-Friends-Rajesh": "Friends & Family",
    "UPI-Friends-Rajkishore": "Friends & Family",
    "UPI-Friends-Ritesh": "Friends & Family",
    "UPI-Friends-Ronak": "Friends & Family",
    "UPI-Friends-Rudra Narayan": "Friends & Family",
    "UPI-Friends-Sashikanta": "Friends & Family",
    "UPI-Friends-Saswat": "Friends & Family",
    "UPI-Friends-Satyajit": "Friends & Family",
    "UPI-Friends-Satyapriya": "Friends & Family",
    "UPI-Friends-Sonal": "Friends & Family",
    "UPI-Friends-Soubhagya": "Friends & Family",
    "UPI-Friends-Sudipta Biswas": "Friends & Family",
    "UPI-Friends-Sumit": "Friends & Family",
    "UPI-Friends-Suraj": "Friends & Family",
    "UPI-Friends-Suresh": "Friends & Family",
    "UPI-Friends-Surya Kant": "Friends & Family",
    
    # Loan Repayment (EMI payments - money going out)
    "Loan Account 1": "Loan Repayment",
    "Loan Account 2": "Loan Repayment",
    
    # Digital Wallets
    "UPI-Wallet-Amazon": "Digital Wallets",
    "UPI-Wallet-Gpay": "Digital Wallets",
    "UPI-Wallet-Paytm": "Digital Wallets",
    
    # Technology & Services
    "UPI-Misc-Tech-Uni Pay": "Technology & Services",
    "UNI PAY": "Technology & Services",
    
    # Others/Miscellaneous
    "Others": "Miscellaneous",
    "UPI-Others": "Miscellaneous",
    "UPI-Lending-Lipu": "Miscellaneous",
    "Bhagabat": "Miscellaneous",
    "Interest": "Miscellaneous"
}

def detect_bank_format(file_path):
    """Detect bank format by examining file content"""
    try:
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

def map_to_broad_category(category):
    """Map detailed category to broad category"""
    return BROAD_CATEGORIES.get(category, "Miscellaneous")

def map_loan_transactions(df):
    """Separate loan disbursements (credits) from EMI payments (debits)"""
    # Create a copy to avoid modifying original
    df_copy = df.copy()
    
    # Handle loan accounts - separate disbursements from EMI payments
    loan_mask = df_copy['Category'].str.contains('Loan Account', na=False)
    
    for idx in df_copy[loan_mask].index:
        if df_copy.loc[idx, 'Credit'] > 0:
            # Credit = Loan disbursement (money received)
            df_copy.loc[idx, 'Broad_Category'] = 'Income & Salary'
        elif df_copy.loc[idx, 'Debit'] > 0:
            # Debit = EMI payment (money paid)
            df_copy.loc[idx, 'Broad_Category'] = 'Loan Repayment'
    
    return df_copy

def identify_self_transfers(df):
    """Identify and mark self transfers for cancellation"""
    self_transfer_mask = df['Broad_Category'] == 'Self Transfer'
    return df[self_transfer_mask], df[~self_transfer_mask]

def calculate_portfolio_summary(combined_df, debit_col, credit_col):
    """Calculate portfolio-level summary with self-transfer elimination"""
    
    # Separate self transfers from other transactions
    self_transfers, other_transactions = identify_self_transfers(combined_df)
    
    # IGNORE all self-transfer amounts (both credits and debits)
    # Calculate external transactions only (real inflows/outflows)
    external_debits = other_transactions[debit_col].sum()
    external_credits = other_transactions[credit_col].sum()
    net_external = external_credits - external_debits
    
    return {
        'total_transactions': len(combined_df),
        'external_transactions': len(other_transactions),
        'self_transfer_transactions': len(self_transfers),
        'external_outflows': external_debits,
        'external_inflows': external_credits,
        'net_external_change': net_external,
        'self_transfers_ignored': len(self_transfers)
    }

def process_portfolio_files(input_files, output_filename="portfolio_analysis.xlsx"):
    """Process multiple bank files for portfolio analysis"""
    
    files = input_files
    if not files:
        print(f"❌ No files provided")
        return None
    
    files.sort()
    print(f"🔍 Found {len(files)} files to process:")
    for file in files:
        print(f"  - {file}")
    
    all_transactions = []
    
    # Process each file
    for file_path in files:
        print(f"\n📊 Processing {file_path}...")
        try:
            # Create analyzer and use normal flow for categorization
            analyzer = FinanceAnalyzer(file_path)
            analyzer.load_data()
            analyzer.process_transactions()
            
            processed_df = analyzer.categorized_df.copy()
            print(f"  ✅ Loaded and categorized {len(processed_df)} transactions")
            
            # Add metadata
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
    
    # Process dates and years
    combined_df['Txn Date'] = pd.to_datetime(combined_df['Txn Date'], errors='coerce')
    combined_df = combined_df.sort_values('Txn Date')
    combined_df['Year'] = combined_df['Txn Date'].dt.year.astype(str)
    
    # Map to broad categories
    combined_df['Broad_Category'] = combined_df['Category'].apply(map_to_broad_category)
    
    # Handle loan transactions separately (disbursements vs EMI payments)
    combined_df = map_loan_transactions(combined_df)
    
    print(f"✅ Combined {len(combined_df)} total transactions from {len(files)} files")
    
    # Calculate portfolio summary
    print(f"\n📈 Generating portfolio analysis...")
    
    debit_col = 'Debit (₹)' if 'Debit (₹)' in combined_df.columns else 'Debit'
    credit_col = 'Credit (₹)' if 'Credit (₹)' in combined_df.columns else 'Credit'
    
    portfolio_summary = calculate_portfolio_summary(combined_df, debit_col, credit_col)
    
    # Create broad category summary
    broad_category_summary = combined_df.groupby('Broad_Category').agg({
        debit_col: 'sum',
        credit_col: 'sum',
        'Txn Date': 'count'
    }).reset_index()
    broad_category_summary.columns = ['Broad_Category', 'Total_Debits', 'Total_Credits', 'Transaction_Count']
    broad_category_summary['Net_Amount'] = broad_category_summary['Total_Credits'] - broad_category_summary['Total_Debits']
    
    # Enhanced overall summary with highlighted totals at top
    overall_summary = {
        'TOTAL_EARNED': portfolio_summary['external_inflows'],
        'TOTAL_SPENT': portfolio_summary['external_outflows'],
        'NET_PORTFOLIO_CHANGE': portfolio_summary['net_external_change'],
        '---SEPARATOR---': '---',
        'total_transactions': portfolio_summary['total_transactions'],
        'external_transactions': portfolio_summary['external_transactions'],
        'self_transfer_transactions': portfolio_summary['self_transfer_transactions'],
        'external_outflows': portfolio_summary['external_outflows'],
        'external_inflows': portfolio_summary['external_inflows'],
        'net_portfolio_change': portfolio_summary['net_external_change'],
        'self_transfers_ignored': portfolio_summary['self_transfers_ignored'],
        'date_range_start': combined_df['Txn Date'].min().strftime('%Y-%m-%d') if pd.notna(combined_df['Txn Date'].min()) else 'N/A',
        'date_range_end': combined_df['Txn Date'].max().strftime('%Y-%m-%d') if pd.notna(combined_df['Txn Date'].max()) else 'N/A',
        'report_generated_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Output to visuals directory
    if Path("visuals").exists():
        output_path = Path("visuals") / output_filename
    else:
        output_path = Path("../visuals") / output_filename
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write enhanced Excel report
    writer = ExcelWriter(str(output_path))
    writer.write_analysis_report(combined_df, overall_summary, broad_category_summary)
    
    # Print portfolio summary (ignoring self-transfers)
    print(f"\n📊 PORTFOLIO SUMMARY (Self-Transfers Ignored):")
    print(f"   Total Transactions: {portfolio_summary['total_transactions']:,}")
    print(f"   External Transactions: {portfolio_summary['external_transactions']:,}")
    print(f"   Self Transfers (Ignored): {portfolio_summary['self_transfer_transactions']:,}")
    print(f"   External Inflows: ₹{portfolio_summary['external_inflows']:,.2f}")
    print(f"   External Outflows: ₹{portfolio_summary['external_outflows']:,.2f}")
    print(f"   Net Portfolio Change: ₹{portfolio_summary['net_external_change']:,.2f}")
    
    print(f"\n💡 NOTE: All self-transfer transactions have been completely ignored")
    print(f"   This shows only true external income and spending across all accounts")
    
    # Top spending categories (excluding self transfers)
    print(f"\n🏷️  TOP SPENDING CATEGORIES:")
    spending_categories = broad_category_summary[broad_category_summary['Broad_Category'] != 'Self Transfer']
    spending_categories = spending_categories.sort_values('Total_Debits', ascending=False).head(8)
    for _, row in spending_categories.iterrows():
        print(f"   {row['Broad_Category']}: ₹{row['Total_Debits']:,.2f}")
    
    print(f"\n✅ Portfolio analysis complete! Results saved to: {output_path}")
    return str(output_path)

def main():
    """Main function for portfolio analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Portfolio Financial Analyzer')
    parser.add_argument('--input', nargs='+', required=True, 
                       help='Input files to process (e.g., --input data/SBI_2024.xls data/bank_statement.csv)')
    parser.add_argument('--output', default='portfolio_analysis.xlsx',
                       help='Output filename (default: portfolio_analysis.xlsx)')
    
    args = parser.parse_args()
    
    # Handle paths correctly whether running from root or src directory
    input_files = []
    for file in args.input:
        if Path(file).exists():
            input_files.append(file)
        elif Path(f"../{file}").exists():
            input_files.append(f"../{file}")
        else:
            input_files.append(file)
    
    print("🚀 Portfolio Financial Analyzer")
    print("=" * 50)
    
    result = process_portfolio_files(input_files, args.output)
    
    if result:
        print(f"\n🎉 Portfolio analysis completed successfully!")
        print(f"📁 Output file: {result}")
    else:
        print(f"\n❌ Portfolio analysis failed!")

if __name__ == "__main__":
    main()
