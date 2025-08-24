#!/usr/bin/env python3
"""
CLI Tool for PDF Statement Parser
Simple command-line interface for parsing PDF statements and reconciliation
"""

import argparse
import os
import sys
from pdf_statement_parser import ImprovedPDFParser
from statement_reconciliation import StatementReconciler

def parse_statements(input_dir, output_dir):
    """Parse PDF statements"""
    print(f"Parsing PDF statements from: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    parser = ImprovedPDFParser()
    
    # Parse all statements
    parsed_data = parser.scan_and_parse_statements(input_dir)
    
    if not parsed_data:
        print("No PDF statements found or parsed successfully.")
        return False
    
    # Save results
    parser.save_parsed_data(parsed_data, output_dir)
    
    # Print summary
    print("\n=== PARSING SUMMARY ===")
    total_statements = 0
    total_transactions = 0
    
    for key, statements in parsed_data.items():
        stmt_count = len(statements)
        txn_count = sum(len(s.transactions) for s in statements)
        total_statements += stmt_count
        total_transactions += txn_count
        
        print(f"{key}: {stmt_count} statements, {txn_count} transactions")
    
    print(f"\nTotal: {total_statements} statements, {total_transactions} transactions")
    return True

def reconcile_statements(statements_dir, email_file, output_file):
    """Reconcile PDF statements with email transactions"""
    print(f"Reconciling statements from: {statements_dir}")
    print(f"Email transactions: {email_file}")
    print(f"Output report: {output_file}")
    
    if not os.path.exists(email_file):
        print(f"Error: Email transactions file not found: {email_file}")
        return False
    
    reconciler = StatementReconciler()
    
    # Load data
    pdf_data = reconciler.load_pdf_statements(statements_dir)
    email_data = reconciler.load_email_transactions(email_file)
    
    if not pdf_data:
        print("No PDF statement data found.")
        return False
    
    if not email_data:
        print("No email transaction data found.")
        return False
    
    # Reconcile
    matches = reconciler.reconcile_statements(pdf_data, email_data)
    
    # Generate report
    report = reconciler.generate_reconciliation_report(matches, output_file)
    
    # Print summary
    reconciler.print_summary(report)
    
    return True

def main():
    parser = argparse.ArgumentParser(description='PDF Statement Parser and Reconciliation Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse PDF statements')
    parse_parser.add_argument('input_dir', help='Directory containing PDF statements')
    parse_parser.add_argument('-o', '--output', 
                            default='/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/statements',
                            help='Output directory for parsed JSON files')
    
    # Reconcile command
    reconcile_parser = subparsers.add_parser('reconcile', help='Reconcile statements with email transactions')
    reconcile_parser.add_argument('-s', '--statements', 
                                default='/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/statements',
                                help='Directory containing parsed statement JSON files')
    reconcile_parser.add_argument('-e', '--email',
                                default='/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/email_transactions.json',
                                help='Email transactions JSON file')
    reconcile_parser.add_argument('-o', '--output',
                                default='/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/reconciliation_report.json',
                                help='Output reconciliation report file')
    
    # Both command
    both_parser = subparsers.add_parser('both', help='Parse statements and reconcile')
    both_parser.add_argument('input_dir', help='Directory containing PDF statements')
    both_parser.add_argument('-s', '--statements-output',
                           default='/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/statements',
                           help='Output directory for parsed JSON files')
    both_parser.add_argument('-e', '--email',
                           default='/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/email_transactions.json',
                           help='Email transactions JSON file')
    both_parser.add_argument('-r', '--reconcile-output',
                           default='/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/reconciliation_report.json',
                           help='Output reconciliation report file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'parse':
        if not os.path.exists(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}")
            sys.exit(1)
        
        success = parse_statements(args.input_dir, args.output)
        sys.exit(0 if success else 1)
    
    elif args.command == 'reconcile':
        if not os.path.exists(args.statements):
            print(f"Error: Statements directory not found: {args.statements}")
            sys.exit(1)
        
        success = reconcile_statements(args.statements, args.email, args.output)
        sys.exit(0 if success else 1)
    
    elif args.command == 'both':
        if not os.path.exists(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}")
            sys.exit(1)
        
        # Parse first
        print("Step 1: Parsing PDF statements...")
        success = parse_statements(args.input_dir, args.statements_output)
        if not success:
            sys.exit(1)
        
        print("\nStep 2: Reconciling with email transactions...")
        success = reconcile_statements(args.statements_output, args.email, args.reconcile_output)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
