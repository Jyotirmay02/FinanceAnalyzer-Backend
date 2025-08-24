#!/usr/bin/env python3
"""
PDF Statement Parser for Financial Reconciliation
Extracts transaction data from bank and credit card statements
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import PyPDF2
import pdfplumber
from pathlib import Path

@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    type: str  # credit|debit
    balance: Optional[float] = None
    reference: Optional[str] = None
    merchant_category: Optional[str] = None
    reward_points: Optional[int] = None

@dataclass
class StatementSummary:
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    reward_points_opening: Optional[int] = None
    reward_points_earned: Optional[int] = None
    reward_points_redeemed: Optional[int] = None
    reward_points_closing: Optional[int] = None

@dataclass
class StatementData:
    account_type: str  # savings|salary|credit_card
    bank: str
    account_number: str
    statement_period: Dict[str, str]
    transactions: List[Transaction]
    summary: StatementSummary

class PDFStatementParser:
    def __init__(self):
        self.bank_patterns = {
            'sbi': {
                'name': 'State Bank of India',
                'account_pattern': r'Account No[:\s]+(\d+)',
                'date_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})',
                'amount_pattern': r'([\d,]+\.\d{2})',
                'transaction_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?\s*([\d,]+\.\d{2})?'
            },
            'hdfc': {
                'name': 'HDFC Bank',
                'account_pattern': r'(\d{4}\s*XXXX\s*XXXX\s*\d{2,4})',
                'date_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})',
                'amount_pattern': r'([\d,]+\.\d{2})',
                'transaction_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?'
            },
            'indusind': {
                'name': 'IndusInd Bank',
                'account_pattern': r'Card No[:\s]+(\d+)',
                'date_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})',
                'amount_pattern': r'([\d,]+\.\d{2})',
                'transaction_pattern': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([A-Z\s&]+?)\s+(\d+)\s+([\d,]+\.\d{2})\s+(CR|DR)',
                'payment_pattern': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+)\s+([\d,]+\.\d{2})\s+(CR|DR)'
            },
            'kotak': {
                'name': 'Kotak Mahindra Bank',
                'account_pattern': r'Account No[:\s]+(\d+)',
                'date_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})',
                'amount_pattern': r'([\d,]+\.\d{2})',
                'transaction_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?'
            },
            'canara': {
                'name': 'Canara Bank',
                'account_pattern': r'Account No[:\s]+(\d+)',
                'date_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})',
                'amount_pattern': r'([\d,]+\.\d{2})',
                'transaction_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?'
            },
            'icici': {
                'name': 'ICICI Bank',
                'account_pattern': r'Account No[:\s]+(\d+)',
                'date_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})',
                'amount_pattern': r'([\d,]+\.\d{2})',
                'transaction_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?'
            }
        }

    def detect_bank(self, text: str) -> str:
        """Detect bank from PDF text"""
        text_lower = text.lower()
        
        # More specific patterns for better detection
        if 'hdfc bank' in text_lower or 'hdfc credit card' in text_lower:
            return 'hdfc'
        elif 'state bank of india' in text_lower or 'sbi' in text_lower or 'regular sb chq' in text_lower:
            return 'sbi'
        elif 'indusind bank' in text_lower or 'indusind' in text_lower:
            return 'indusind'
        elif 'kotak mahindra' in text_lower or 'kotak' in text_lower:
            return 'kotak'
        elif 'canara bank' in text_lower or 'canara' in text_lower:
            return 'canara'
        elif 'icici bank' in text_lower or 'icici' in text_lower:
            return 'icici'
        return 'unknown'

    def detect_account_type(self, text: str, filename: str) -> str:
        """Detect account type from content and filename"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Check filename first for clear indicators
        if any(x in filename_lower for x in ['cc_stmt', 'credit_card', 'diners', 'millenia', 'platinum']):
            return 'credit_card'
        elif 'salary' in filename_lower:
            return 'salary'
        
        # Check content
        if any(x in text_lower for x in ['credit card', 'card statement', 'card no:', 'total dues', 'minimum amount due']):
            return 'credit_card'
        elif any(x in text_lower for x in ['salary account', 'salary credit']):
            return 'salary'
        elif any(x in text_lower for x in ['savings account', 'regular sb', 'saving account']):
            return 'savings'
        
        # Default based on directory structure
        if 'credit card' in filename_lower or '/credit card/' in filename_lower.replace('\\', '/'):
            return 'credit_card'
        
        return 'savings'  # Default

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple methods"""
        text = ""
        
        # Try pdfplumber first (better for tables)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"pdfplumber failed for {pdf_path}: {e}")
        
        # Fallback to PyPDF2
        if not text.strip():
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            except Exception as e:
                print(f"PyPDF2 failed for {pdf_path}: {e}")
        
        return text

    def parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        if not amount_str:
            return 0.0
        # Remove commas and convert to float
        cleaned = re.sub(r'[,\s]', '', amount_str)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def standardize_date(self, date_str: str) -> str:
        """Convert date to YYYY-MM-DD format"""
        # Handle various date formats
        date_formats = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str  # Return as-is if parsing fails

    def extract_transactions_indusind(self, text: str) -> List[Transaction]:
        """Extract transactions specifically for IndusInd Bank statements"""
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Pattern for regular transactions with merchant category and points
            # Format: DD/MM/YYYY DESCRIPTION MERCHANT_CATEGORY POINTS AMOUNT CR/DR
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([A-Z\s&]+?)\s+(\d+)\s+([\d,]+\.\d{2})\s+(CR|DR)', line)
            if match:
                date_str = match.group(1)
                description = match.group(2).strip()
                merchant_category = match.group(3).strip()
                points = int(match.group(4))
                amount_str = match.group(5)
                cr_dr = match.group(6)
                
                amount = self.parse_amount(amount_str)
                trans_type = 'credit' if cr_dr == 'CR' else 'debit'
                
                transaction = Transaction(
                    date=self.standardize_date(date_str),
                    description=description,
                    amount=amount,
                    type=trans_type,
                    merchant_category=merchant_category,
                    reward_points=points
                )
                transactions.append(transaction)
                continue
            
            # Pattern for payments (no merchant category)
            # Format: DD/MM/YYYY DESCRIPTION POINTS AMOUNT CR/DR
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+)\s+([\d,]+\.\d{2})\s+(CR|DR)', line)
            if match:
                date_str = match.group(1)
                description = match.group(2).strip()
                points = int(match.group(3))
                amount_str = match.group(4)
                cr_dr = match.group(5)
                
                # Skip if this looks like a regular transaction (has merchant category words)
                if any(cat in description.upper() for cat in ['RESTAURANTS', 'GROCERY', 'UTILITIES', 'PERSONAL CARE']):
                    continue
                
                amount = self.parse_amount(amount_str)
                trans_type = 'credit' if cr_dr == 'CR' else 'debit'
                
                transaction = Transaction(
                    date=self.standardize_date(date_str),
                    description=description,
                    amount=amount,
                    type=trans_type,
                    reward_points=points
                )
                transactions.append(transaction)
        
        return transactions
        """Generic transaction extraction"""
        transactions = []
        patterns = self.bank_patterns.get(bank, self.bank_patterns['sbi'])
        
        # Split text into lines and process
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for transaction patterns
            match = re.search(patterns['transaction_pattern'], line)
            if match:
                date_str = match.group(1)
                description = match.group(2).strip()
                amount_str = match.group(3)
                cr_dr = match.group(4) if len(match.groups()) > 3 else None
                balance_str = match.group(5) if len(match.groups()) > 4 else None
                
                # Skip header lines
                if any(x in description.lower() for x in ['date', 'description', 'amount', 'balance']):
                    continue
                
                amount = self.parse_amount(amount_str)
                balance = self.parse_amount(balance_str) if balance_str else None
                
                # Determine transaction type
                trans_type = 'credit' if cr_dr == 'Cr' else 'debit'
                
                transaction = Transaction(
                    date=self.standardize_date(date_str),
                    description=description,
                    amount=amount,
                    type=trans_type,
                    balance=balance,
                    reference=None
                )
                transactions.append(transaction)
        
        return transactions

    def extract_statement_period(self, text: str) -> Dict[str, str]:
        """Extract statement period from text"""
        # Look for date ranges
        period_patterns = [
            r'Statement Period[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})\s+to\s+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'From[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})\s+To[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'(\d{2}[/-]\d{2}[/-]\d{4})\s+to\s+(\d{2}[/-]\d{2}[/-]\d{4})'
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_date = self.standardize_date(match.group(1))
                end_date = self.standardize_date(match.group(2))
                return {"start": start_date, "end": end_date}
        
        return {"start": "", "end": ""}

    def extract_account_number(self, text: str, bank: str) -> str:
        """Extract account number from text"""
        patterns = self.bank_patterns.get(bank, {})
        account_pattern = patterns.get('account_pattern', r'Account No[:\s]+(\d+)')
        
        match = re.search(account_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return "XXXX"

    def calculate_summary(self, transactions: List[Transaction], text: str) -> StatementSummary:
        """Calculate statement summary"""
        total_credits = sum(t.amount for t in transactions if t.type == 'credit')
        total_debits = sum(t.amount for t in transactions if t.type == 'debit')
        
        # Try to extract opening/closing balance from text
        opening_balance = 0.0
        closing_balance = 0.0
        
        # Look for balance patterns
        balance_patterns = [
            r'Opening Balance[:\s]+([\d,]+\.\d{2})',
            r'Closing Balance[:\s]+([\d,]+\.\d{2})',
            r'Previous Balance[:\s]+([\d,]+\.\d{2})',
            r'Current Balance[:\s]+([\d,]+\.\d{2})'
        ]
        
        for pattern in balance_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if 'opening' in pattern.lower() or 'previous' in pattern.lower():
                    opening_balance = self.parse_amount(matches[0])
                elif 'closing' in pattern.lower() or 'current' in pattern.lower():
                    closing_balance = self.parse_amount(matches[-1])
        
        # If we have transactions with balances, use the first and last
        if transactions:
            balances = [t.balance for t in transactions if t.balance is not None]
            if balances:
                if opening_balance == 0.0:
                    opening_balance = balances[0]
                if closing_balance == 0.0:
                    closing_balance = balances[-1]
        
        return StatementSummary(
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits
        )

    def parse_pdf_statement(self, pdf_path: str) -> Optional[StatementData]:
        """Parse a single PDF statement"""
        try:
            print(f"Parsing: {pdf_path}")
            
            # Extract text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            if not text.strip():
                print(f"No text extracted from {pdf_path}")
                return None
            
            # Detect bank and account type
            filename = os.path.basename(pdf_path)
            bank = self.detect_bank(text)
            account_type = self.detect_account_type(text, filename)
            
            print(f"Detected: {bank} {account_type}")
            
            # Extract data
            account_number = self.extract_account_number(text, bank)
            statement_period = self.extract_statement_period(text)
            transactions = self.extract_transactions_generic(text, bank)
            summary = self.calculate_summary(transactions, text)
            
            bank_name = self.bank_patterns.get(bank, {}).get('name', bank.upper())
            
            statement_data = StatementData(
                account_type=account_type,
                bank=bank_name,
                account_number=account_number,
                statement_period=statement_period,
                transactions=transactions,
                summary=summary
            )
            
            print(f"Extracted {len(transactions)} transactions")
            return statement_data
            
        except Exception as e:
            print(f"Error parsing {pdf_path}: {e}")
            return None

    def scan_and_parse_statements(self, base_dir: str) -> Dict[str, List[StatementData]]:
        """Scan directory and parse all PDF statements"""
        results = {}
        
        # Find all PDF files
        pdf_files = []
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        print(f"Found {len(pdf_files)} PDF files")
        
        for pdf_path in pdf_files:
            statement_data = self.parse_pdf_statement(pdf_path)
            if statement_data:
                key = f"{statement_data.bank}_{statement_data.account_type}"
                if key not in results:
                    results[key] = []
                results[key].append(statement_data)
        
        return results

    def save_parsed_data(self, parsed_data: Dict[str, List[StatementData]], output_dir: str):
        """Save parsed data to JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        current_month = datetime.now().strftime('%Y%m')
        
        for key, statements in parsed_data.items():
            # Convert to dict format
            output_data = []
            for statement in statements:
                statement_dict = asdict(statement)
                # Convert Transaction objects to dicts
                statement_dict['transactions'] = [asdict(t) for t in statement.transactions]
                statement_dict['summary'] = asdict(statement.summary)
                output_data.append(statement_dict)
            
            # Save to file
            filename = f"statement_data_{key}_{current_month}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"Saved {len(output_data)} statements to {filepath}")

def main():
    """Main function to run the parser"""
    parser = PDFStatementParser()
    
    # Paths
    base_dir = "/Users/jmysethi/Documents/Finance/Financial Records"
    output_dir = "/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/statements"
    
    print("Starting PDF Statement Parser...")
    print(f"Scanning directory: {base_dir}")
    
    # Parse all statements
    parsed_data = parser.scan_and_parse_statements(base_dir)
    
    # Save results
    parser.save_parsed_data(parsed_data, output_dir)
    
    # Print summary
    print("\n=== PARSING SUMMARY ===")
    for key, statements in parsed_data.items():
        print(f"{key}: {len(statements)} statements")
        for statement in statements:
            print(f"  - {statement.statement_period['start']} to {statement.statement_period['end']}: {len(statement.transactions)} transactions")

if __name__ == "__main__":
    main()
