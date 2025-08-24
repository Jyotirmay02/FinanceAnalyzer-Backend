#!/usr/bin/env python3
"""
Improved PDF Statement Parser with proper CR/DR detection and reward points
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
class AccountSummary:
    previous_balance: Optional[float] = None
    purchases_and_charges: Optional[float] = None
    cash_advance: Optional[float] = None
    payments_and_credits: Optional[float] = None
    total_amount_due: Optional[float] = None
    minimum_amount_due: Optional[float] = None
    credit_limit: Optional[float] = None
    available_credit_limit: Optional[float] = None
    cash_limit: Optional[float] = None
    available_cash_limit: Optional[float] = None

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
    account_summary: Optional[AccountSummary] = None

@dataclass
class StatementData:
    account_type: str  # savings|salary|credit_card
    bank: str
    account_number: str
    statement_period: Dict[str, str]
    transactions: List[Transaction]
    summary: StatementSummary

class ImprovedPDFParser:
    def __init__(self):
        self.bank_patterns = {
            'indusind': {
                'name': 'IndusInd Bank',
                'account_pattern': r'Card No[:\s]+(\d+)',
            },
            'hdfc': {
                'name': 'HDFC Bank',
                'account_pattern': r'(\d{4}\s*XXXX\s*XXXX\s*\d{2,4})',
            },
            'sbi': {
                'name': 'State Bank of India',
                'account_pattern': r'Account No[:\s]+(\d+)',
            }
        }

    def detect_bank(self, text: str) -> str:
        """Detect bank from PDF text"""
        text_lower = text.lower()
        
        if 'hdfc bank' in text_lower or 'hdfc credit card' in text_lower:
            return 'hdfc'
        elif 'indusind bank' in text_lower or 'indusind' in text_lower:
            return 'indusind'
        elif 'state bank of india' in text_lower or 'sbi' in text_lower or 'regular sb chq' in text_lower:
            return 'sbi'
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
        
        if any(x in filename_lower for x in ['cc_stmt', 'credit_card', 'diners', 'millenia', 'platinum']):
            return 'credit_card'
        elif 'salary' in filename_lower:
            return 'salary'
        
        if any(x in text_lower for x in ['credit card', 'card statement', 'card no:', 'total dues', 'minimum amount due']):
            return 'credit_card'
        elif any(x in text_lower for x in ['salary account', 'salary credit']):
            return 'salary'
        elif any(x in text_lower for x in ['savings account', 'regular sb', 'saving account']):
            return 'savings'
        
        if 'credit card' in filename_lower or '/credit card/' in filename_lower.replace('\\', '/'):
            return 'credit_card'
        
        return 'savings'

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple methods"""
        text = ""
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"pdfplumber failed for {pdf_path}: {e}")
        
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
        cleaned = re.sub(r'[,\s]', '', amount_str)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def standardize_date(self, date_str: str) -> str:
        """Convert date to YYYY-MM-DD format"""
        date_formats = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str

    def extract_indusind_transactions(self, text: str) -> List[Transaction]:
        """Extract IndusInd transactions with proper CR/DR and merchant category"""
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Pattern for regular transactions: DATE DESCRIPTION MERCHANT_CATEGORY POINTS AMOUNT CR/DR
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
            
            # Pattern for payments: DATE DESCRIPTION POINTS AMOUNT CR/DR
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+)\s+([\d,]+\.\d{2})\s+(CR|DR)', line)
            if match:
                date_str = match.group(1)
                description = match.group(2).strip()
                points = int(match.group(3))
                amount_str = match.group(4)
                cr_dr = match.group(5)
                
                # Skip if this looks like a regular transaction
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

    def extract_sbi_transactions(self, text: str) -> List[Transaction]:
        """Extract SBI transactions with proper C/D detection"""
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            # SBI transaction pattern: Date Description Amount C/D
            match = re.match(r'(\d{2}\s+\w{3}\s+\d{2})\s+(.+?)\s+([\d,]+\.?\d*)\s+([CD])$', line.strip())
            if match:
                date_str, description, amount_str, type_code = match.groups()
                
                try:
                    # Convert date format
                    date_obj = datetime.strptime(date_str + ' 2023', '%d %b %y %Y')  # Assuming 2023
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    amount = self.parse_amount(amount_str)
                    txn_type = 'credit' if type_code == 'C' else 'debit'
                    
                    transaction = Transaction(
                        date=formatted_date,
                        description=description.strip(),
                        amount=amount,
                        type=txn_type,
                        merchant_category=None,  # Keep null as requested
                        reward_points=0  # SBI doesn't show per-transaction points
                    )
                    transactions.append(transaction)
                    
                except Exception as e:
                    print(f"Error parsing SBI transaction: {line} - {e}")
                    continue
        
        return transactions
    
    def extract_account_summary_sbi(self, text: str) -> AccountSummary:
        """Extract account summary from SBI statement"""
        summary = AccountSummary()
        lines = text.split('\n')
        
        # Extract credit card number from top right - line 2: "XXXX XXXX XXXX XX29"
        for i, line in enumerate(lines[:5]):
            if 'XXXX XXXX XXXX' in line:
                summary.account_number = line.strip()
                break
        
        # Extract credit limits - line 10: "1,00,000.00 10,000.00 16 Feb 2023"
        for line in lines:
            if 'Credit Limit(' in line and 'Cash Limit(' in line:
                # Next line should have amounts
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    amounts = re.findall(r'([\d,]+\.?\d*)', lines[idx + 1])
                    if len(amounts) >= 2:
                        summary.credit_limit = amounts[0]
                        summary.cash_limit = amounts[1]
            elif 'Available Credit Limit(' in line:
                # Next line should have amounts  
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    amounts = re.findall(r'([\d,]+\.?\d*)', lines[idx + 1])
                    if len(amounts) >= 2:
                        summary.available_credit_limit = amounts[0]
                        summary.available_cash_limit = amounts[1]
        
        # Extract account summary - line 19: "9,103.54 9,425.00 18,296.89 0.00 17,975.00"
        for i, line in enumerate(lines):
            if 'Previous Balance Reversals & other' in line and 'Total Outstanding' in line:
                # Skip the currency line and get amounts from next line
                if i+2 < len(lines):
                    amounts = re.findall(r'([\d,]+\.?\d*)', lines[i+2])
                    if len(amounts) >= 5:
                        summary.previous_balance = float(amounts[0].replace(',', ''))
                        summary.payments_and_credits = float(amounts[1].replace(',', ''))
                        summary.purchases_and_charges = float(amounts[2].replace(',', ''))
                        summary.cash_advance = float(amounts[3].replace(',', ''))  # Fees/taxes
                        summary.total_amount_due = float(amounts[4].replace(',', ''))
                        break
        
        # Extract minimum amount due - line 8: "899.00"
        for i, line in enumerate(lines):
            if 'Minimum Amount Due(' in line:
                # Look for amount in next few lines
                for j in range(i+1, min(i+4, len(lines))):
                    amount_match = re.search(r'^([\d,]+\.?\d*)$', lines[j].strip())
                    if amount_match:
                        summary.minimum_amount_due = amount_match.group(1)
                        break
                break
        
        return summary

    def extract_reward_points_summary(self, text: str, bank: str) -> Dict[str, int]:
        """Extract reward points summary"""
        points_data = {}
        
        if bank == 'indusind':
            # Look for the specific pattern in IndusInd statements
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'rewards' in line.lower() and ('openingbalance' in line.lower() or 'opening' in line.lower()):
                    # Check next few lines for the numbers
                    for j in range(i+1, min(i+5, len(lines))):
                        # Pattern: 3222 560 -842 4624
                        match = re.search(r'^(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)$', lines[j].strip())
                        if match:
                            points_data = {
                                'opening': int(match.group(1)),
                                'earned': int(match.group(2)),
                                'redeemed': abs(int(match.group(3))),
                                'closing': int(match.group(4))
                            }
                            break
                    break
        
    def extract_account_summary_indusind(self, text: str) -> AccountSummary:
        """Extract account summary from IndusInd statement"""
        summary = AccountSummary()
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if 'previous balance' in line.lower():
                # Extract values from the summary section
                try:
                    # Previous Balance (next line after "Previous Balance")
                    if i+1 < len(lines):
                        prev_balance_line = lines[i+1].strip()
                        match = re.search(r'([\d,]+\.\d{2})', prev_balance_line)
                        if match:
                            summary.previous_balance = self.parse_amount(match.group(1))
                    
                    # Purchases & Other Charges (skip "Purchases & Other Charges" line, get next)
                    if i+3 < len(lines):
                        purchases_line = lines[i+3].strip()
                        match = re.search(r'([\d,]+\.\d{2})', purchases_line)
                        if match:
                            summary.purchases_and_charges = self.parse_amount(match.group(1))
                    
                    # Cash Advance
                    if i+5 < len(lines):
                        cash_line = lines[i+5].strip()
                        match = re.search(r'([\d,]+\.\d{2})', cash_line)
                        if match:
                            summary.cash_advance = self.parse_amount(match.group(1))
                    
                    # Payment & Other Credits
                    if i+7 < len(lines):
                        payment_line = lines[i+7].strip()
                        # Look for the payment amount (usually the large number)
                        amounts = re.findall(r'([\d,]+\.\d{2})', payment_line)
                        if amounts:
                            summary.payments_and_credits = self.parse_amount(amounts[0])
                    
                    # Credit limits (from Summary line)
                    if i+9 < len(lines):
                        summary_line = lines[i+9].strip()
                        amounts = re.findall(r'([\d,]+\.\d{2})', summary_line)
                        if len(amounts) >= 4:
                            summary.credit_limit = self.parse_amount(amounts[0])
                            summary.available_credit_limit = self.parse_amount(amounts[1])
                            summary.cash_limit = self.parse_amount(amounts[2])
                            summary.available_cash_limit = self.parse_amount(amounts[3])
                    
                    # Total Amount Due and Minimum Amount Due
                    for j in range(i+10, min(len(lines), i+20)):
                        line_text = lines[j].lower()
                        if 'total amount due' in line_text or 'minimum amount due' in line_text:
                            amounts = re.findall(r'([\d,]+\.\d{2})', lines[j])
                            if amounts:
                                if 'minimum amount due' in line_text:
                                    summary.minimum_amount_due = self.parse_amount(amounts[-1])
                                elif 'total amount due' in line_text:
                                    summary.total_amount_due = self.parse_amount(amounts[-1])
                    
                    # Calculate total amount due if not found
                    if summary.total_amount_due is None and all(x is not None for x in [summary.previous_balance, summary.purchases_and_charges, summary.cash_advance, summary.payments_and_credits]):
                        summary.total_amount_due = summary.previous_balance + summary.purchases_and_charges + summary.cash_advance - summary.payments_and_credits
                    
                except Exception as e:
                    print(f"Error extracting account summary: {e}")
                
                break
        
    def extract_hdfc_transactions(self, text: str) -> List[Transaction]:
        """Extract HDFC transactions with proper Cr detection"""
        transactions = []
        lines = text.split('\n')
        
        in_domestic_section = False
        for line in lines:
            if 'Domestic Transactions' in line:
                in_domestic_section = True
                continue
            elif in_domestic_section and ('Reward Points' in line or 'Page' in line):
                break
            elif in_domestic_section:
                # HDFC transaction pattern: Date Description Amount or Amount+Cr
                match = re.match(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.?\d*)(Cr)?$', line.strip())
                if match:
                    date_str, description, amount_str, cr_suffix = match.groups()
                    
                    try:
                        # Convert date format
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                        
                        amount = self.parse_amount(amount_str)
                        txn_type = 'credit' if cr_suffix else 'debit'
                        
                        transaction = Transaction(
                            date=formatted_date,
                            description=description.strip(),
                            amount=amount,
                            type=txn_type,
                            merchant_category=None,
                            reward_points=0
                        )
                        transactions.append(transaction)
                        
                    except Exception as e:
                        print(f"Error parsing HDFC transaction: {line} - {e}")
                        continue
        
        return transactions

    def extract_account_summary_hdfc(self, text: str) -> AccountSummary:
        """Extract account summary from HDFC statement"""
        summary = AccountSummary()
        lines = text.split('\n')
        
        # Extract credit limits - line 12: "2,00,000 1,92,232 80,000"
        for i, line in enumerate(lines):
            if 'Credit Limit' in line and 'Available Credit Limit' in line:
                if i+1 < len(lines):
                    amounts = re.findall(r'([\d,]+)', lines[i+1])
                    if len(amounts) >= 3:
                        summary.credit_limit = amounts[0]
                        summary.available_credit_limit = amounts[1]
                        summary.cash_limit = amounts[2]
                        break
        
        # Extract account summary - line 17: "17,351.83 17,624.73 7,657.22 0.00 7,384.00"
        for i, line in enumerate(lines):
            if 'Account Summary' in line:
                # Skip header lines and get amounts from line after "Balance Credits Debits Charges"
                for j in range(i+1, min(i+5, len(lines))):
                    if 'Balance' in lines[j] and 'Credits' in lines[j] and 'Debits' in lines[j]:
                        if j+1 < len(lines):
                            amounts = re.findall(r'([\d,]+\.?\d*)', lines[j+1])
                            if len(amounts) >= 5:
                                summary.previous_balance = float(amounts[0].replace(',', ''))
                                summary.payments_and_credits = float(amounts[1].replace(',', ''))
                                summary.purchases_and_charges = float(amounts[2].replace(',', ''))
                                summary.cash_advance = float(amounts[3].replace(',', ''))  # Finance charges
                                summary.total_amount_due = float(amounts[4].replace(',', ''))
                                break
                break
        
        # Extract minimum amount due from line 9: "02/10/2024 7,384.00 370.00"
        for line in lines:
            if re.search(r'\d{2}/\d{2}/\d{4}\s+[\d,]+\.?\d*\s+[\d,]+\.?\d*', line):
                amounts = re.findall(r'([\d,]+\.?\d*)', line)
                if len(amounts) >= 2:
                    summary.minimum_amount_due = amounts[-1]  # Last amount is minimum due
                    break
        
        return summary
        
        return summary

    def extract_icici_transactions(self, text: str) -> List[Transaction]:
        """Extract ICICI transactions with proper CR/DR detection"""
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Pattern for ICICI transactions: DD/MM/YYYY SerNo DESCRIPTION Points AMOUNT [CR]
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(.+?)\s+(\d+)\s+([\d,]+\.\d{2})\s*(CR)?', line)
            if match:
                date_str = match.group(1)
                description = match.group(3).strip()
                points = int(match.group(4))
                amount_str = match.group(5)
                is_credit = match.group(6) == 'CR'
                
                amount = self.parse_amount(amount_str)
                trans_type = 'credit' if is_credit else 'debit'
                
                transaction = Transaction(
                    date=self.standardize_date(date_str),
                    description=description,
                    amount=amount,
                    type=trans_type,
                    reward_points=points
                )
                transactions.append(transaction)
        
        return transactions

    def extract_account_summary_icici(self, text: str) -> AccountSummary:
        """Extract account summary from ICICI statement"""
        summary = AccountSummary()
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if 'STATEMENT SUMMARY' in line:
                # Process next 10 lines for account summary data
                for j in range(i+1, min(i+11, len(lines))):
                    current_line = lines[j].strip()
                    
                    # Total Amount due
                    if 'Total Amount due' in current_line:
                        if j+1 < len(lines):
                            amount_match = re.search(r'`([\d,]+\.?\d*)', lines[j+1])
                            if amount_match:
                                summary.total_amount_due = float(amount_match.group(1).replace(',', ''))
                                summary.purchases_and_charges = summary.total_amount_due
                    
                    # Minimum Amount due  
                    elif 'Minimum Amount due' in current_line:
                        if j+1 < len(lines):
                            amount_match = re.search(r'`([\d,]+\.?\d*)', lines[j+1])
                            if amount_match:
                                summary.minimum_amount_due = amount_match.group(1)
                    
                    # Credit limits: look for amounts in next few lines
                    elif 'Credit Limit' in current_line and 'Available Credit' in current_line:
                        for k in range(j+1, min(j+4, len(lines))):
                            amounts = re.findall(r'`([\d,]+\.?\d*)', lines[k])
                            if len(amounts) >= 4:
                                summary.credit_limit = amounts[0]
                                summary.available_credit_limit = amounts[1]
                                summary.cash_limit = amounts[2]
                                summary.available_cash_limit = amounts[3]
                                break
                break
        
        # Look for the breakdown line anywhere in the document
        for i, line in enumerate(lines):
            if 'Previous Balance Purchases / Charges Cash Advances Payments / Credits' in line:
                # The amounts should be in the next line
                if i+1 < len(lines):
                    amounts_line = lines[i+1]
                    amounts = re.findall(r'`([\d,]+\.?\d*)', amounts_line)
                    if len(amounts) >= 4:
                        summary.previous_balance = float(amounts[0].replace(',', ''))
                        summary.purchases_and_charges = float(amounts[1].replace(',', ''))
                        summary.cash_advance = float(amounts[2].replace(',', ''))
                        summary.payments_and_credits = float(amounts[3].replace(',', ''))
                        break
        
        return summary

    def extract_reward_points_summary(self, text: str, bank: str) -> Dict[str, int]:
        """Extract reward points summary"""
        points_data = {}
        
        if bank == 'indusind':
            # IndusInd pattern: OpeningBalance PointsEarned PointsRedeemed ClosingBalance
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'rewards' in line.lower() and ('openingbalance' in line.lower() or 'opening' in line.lower()):
                    for j in range(i+1, min(i+5, len(lines))):
                        match = re.search(r'^(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)$', lines[j].strip())
                        if match:
                            points_data = {
                                'opening': int(match.group(1)),
                                'earned': int(match.group(2)),
                                'redeemed': abs(int(match.group(3))),
                                'closing': int(match.group(4))
                            }
                            break
                    break
        elif bank == 'icici':
            # ICICI pattern: Look for EARNINGS section
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'earnings' in line.lower():
                    # Look for earned points in next few lines
                    for j in range(i+1, min(i+5, len(lines))):
                        # Pattern: 697 697 (earned, transferred)
                        match = re.search(r'^(\d+)\s+(\d+)$', lines[j].strip())
                        if match:
                            points_data = {
                                'earned': int(match.group(1)),
                                'transferred': int(match.group(2))
                            }
                            break
                    break
        
        return points_data

    def extract_statement_period(self, text: str) -> Dict[str, str]:
        """Extract statement period"""
        period_patterns = [
            r'Statement Period[:\s]+(\d{2}/\d{2}/\d{4})\s+[Tt]o\s+(\d{2}/\d{2}/\d{4})',
            r'(\d{2}/\d{2}/\d{4})\s+[Tt]o\s+(\d{2}/\d{2}/\d{4})',
            r'Statement Date:(\d{2}/\d{2}/\d{4})'  # HDFC pattern
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:  # Period range
                    start_date = self.standardize_date(match.group(1))
                    end_date = self.standardize_date(match.group(2))
                    return {"start": start_date, "end": end_date}
                else:  # Single statement date
                    statement_date = self.standardize_date(match.group(1))
                    return {"start": statement_date, "end": statement_date}
        
        return {"start": "", "end": ""}

    def extract_account_number(self, text: str, bank: str) -> str:
        """Extract account/card number from text"""
        if bank == 'indusind':
            # Look for card number pattern: 3561XXXXXXXX1289
            match = re.search(r'(\d{4}XXXX+\d{4})', text)
            if match:
                return match.group(1)
        elif bank == 'hdfc':
            # Look for card number patterns: 0036 1135 XXXX 7469 or 3610 10XXXX 1968
            patterns = [
                r'Card No:\s*(\d{4}\s+\d{4}\s+XXXX\s+\d{4})',  # Millenia format
                r'Card No:\s*(\d{4}\s+\d+XXXX\s+\d+)'         # Diners Club format
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1).replace(' ', '')
            # Fallback pattern
            match = re.search(r'(\d{4}XXXX+\d+)', text)
            if match:
                return match.group(1)
        elif bank == 'icici':
            # Look for card number pattern: 4315XXXXXXXX6007
            match = re.search(r'(\d{4}XXXX+\d{4})', text)
            if match:
                return match.group(1)
        elif bank == 'sbi':
            # Look for SBI card number pattern: XXXX XXXX XXXX XX29
            match = re.search(r'(XXXX XXXX XXXX \w+)', text)
            if match:
                return match.group(1)
        
        # Fallback to generic patterns
        patterns = self.bank_patterns.get(bank, {})
        account_pattern = patterns.get('account_pattern', r'Account No[:\s]+(\d+)')
        
        match = re.search(account_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return "XXXX"

    def calculate_summary(self, transactions: List[Transaction], text: str, bank: str) -> StatementSummary:
        """Calculate statement summary with reward points and account summary"""
        total_credits = sum(t.amount for t in transactions if t.type == 'credit')
        total_debits = sum(t.amount for t in transactions if t.type == 'debit')
        
        # Extract reward points
        points_data = self.extract_reward_points_summary(text, bank) or {}
        
        # Extract account summary for supported banks
        account_summary = None
        if bank == 'indusind':
            account_summary = self.extract_account_summary_indusind(text)
        elif bank == 'hdfc':
            account_summary = self.extract_account_summary_hdfc(text)
        elif bank == 'icici':
            account_summary = self.extract_account_summary_icici(text)
        elif bank == 'sbi':
            account_summary = self.extract_account_summary_sbi(text)
        
        return StatementSummary(
            opening_balance=0.0,
            closing_balance=0.0,
            total_credits=total_credits,
            total_debits=total_debits,
            reward_points_opening=points_data.get('opening'),
            reward_points_earned=points_data.get('earned'),
            reward_points_redeemed=points_data.get('redeemed'),
            reward_points_closing=points_data.get('closing'),
            account_summary=account_summary
        )

    def parse_pdf_statement(self, pdf_path: str) -> Optional[StatementData]:
        """Parse a single PDF statement"""
        try:
            print(f"Parsing: {pdf_path}")
            
            text = self.extract_text_from_pdf(pdf_path)
            if not text.strip():
                print(f"No text extracted from {pdf_path}")
                return None
            
            filename = os.path.basename(pdf_path)
            bank = self.detect_bank(text)
            account_type = self.detect_account_type(text, filename)
            
            print(f"Detected: {bank} {account_type}")
            
            # Use bank-specific extraction
            if bank == 'indusind':
                transactions = self.extract_indusind_transactions(text)
            elif bank == 'hdfc':
                transactions = self.extract_hdfc_transactions(text)
            elif bank == 'icici':
                transactions = self.extract_icici_transactions(text)
            elif bank == 'sbi':
                transactions = self.extract_sbi_transactions(text)
            else:
                transactions = []  # Add other bank parsers as needed
            
            account_number = self.extract_account_number(text, bank)
            statement_period = self.extract_statement_period(text)
            summary = self.calculate_summary(transactions, text, bank)
            
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

    def process_icici_statements(self) -> Dict:
        """Process all ICICI statements and return results"""
        icici_dir = "statements/ICICI"
        results = {"transactions": [], "account_summaries": []}
        
        if not os.path.exists(icici_dir):
            print(f"ICICI directory not found: {icici_dir}")
            return results
            
        pdf_files = [f for f in os.listdir(icici_dir) if f.endswith('.pdf')]
        print(f"Found {len(pdf_files)} ICICI PDF files")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(icici_dir, pdf_file)
            try:
                text = self.extract_text_from_pdf(pdf_path)
                transactions = self.extract_icici_transactions(text)
                account_summary = self.extract_account_summary_icici(text)
                
                # Convert to dict format
                for txn in transactions:
                    results["transactions"].append({
                        "date": txn.date,
                        "description": txn.description,
                        "amount": txn.amount,
                        "type": txn.type,
                        "merchant_category": txn.merchant_category,
                        "reward_points": txn.reward_points
                    })
                
                # Convert account summary to dict
                if account_summary:
                    results["account_summaries"].append({
                        "credit_limit": account_summary.credit_limit,
                        "available_credit_limit": account_summary.available_credit_limit,
                        "minimum_amount_due": account_summary.minimum_amount_due,
                        "previous_balance": account_summary.previous_balance,
                        "purchases_and_charges": account_summary.purchases_and_charges,
                        "payments_and_credits": account_summary.payments_and_credits
                    })
                    
            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
                
        return results

    def save_parsed_data(self, parsed_data: Dict[str, List[StatementData]], output_dir: str):
        """Save parsed data to JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        current_month = datetime.now().strftime('%Y%m')
        
        for key, statements in parsed_data.items():
            output_data = []
            for statement in statements:
                statement_dict = asdict(statement)
                # Convert Transaction objects to dicts
                statement_dict['transactions'] = [asdict(t) for t in statement.transactions]
                # Convert StatementSummary to dict (handles nested AccountSummary)
                summary_dict = asdict(statement.summary)
                if statement.summary.account_summary:
                    summary_dict['account_summary'] = asdict(statement.summary.account_summary)
                statement_dict['summary'] = summary_dict
                output_data.append(statement_dict)
            
            filename = f"statement_data_{key}_{current_month}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"Saved {len(output_data)} statements to {filepath}")

def main():
    """Process all credit card statements with enhanced parsing"""
    parser = ImprovedPDFParser()
    
    base_dir = "/Users/jmysethi/Documents/Finance/Financial Records"
    output_dir = "/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/statements/creditcard"
    
    print("Processing all credit card statements with enhanced parsing...")
    
    # Define credit card directories
    cc_banks = {
        'IndusInd': 'Credit Card/Indusind',
        'HDFC': 'Credit Card/HDFC', 
        'ICICI': 'Credit Card/ICICI',
        'SBI': 'Credit Card/SBI'
    }
    
    all_parsed_data = {}
    
    for bank_name, bank_dir in cc_banks.items():
        bank_path = os.path.join(base_dir, bank_dir)
        if not os.path.exists(bank_path):
            print(f"Directory not found: {bank_path}")
            continue
            
        # Find PDF files for this bank
        pdf_files = []
        for root, dirs, files in os.walk(bank_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        print(f"\\nProcessing {bank_name}: Found {len(pdf_files)} PDF files")
        
        parsed_statements = []
        for pdf_path in pdf_files:
            statement = parser.parse_pdf_statement(pdf_path)
            if statement:
                parsed_statements.append(statement)
        
        if parsed_statements:
            key = f"{parsed_statements[0].bank}_credit_card"
            all_parsed_data[key] = parsed_statements
            
            # Print summary for this bank
            total_transactions = sum(len(s.transactions) for s in parsed_statements)
            total_credits = sum(s.summary.total_credits for s in parsed_statements)
            total_debits = sum(s.summary.total_debits for s in parsed_statements)
            
            print(f"  Processed: {len(parsed_statements)} statements")
            print(f"  Transactions: {total_transactions}")
            print(f"  Credits: ₹{total_credits:,.2f}")
            print(f"  Debits: ₹{total_debits:,.2f}")
    
    # Save all parsed data
    if all_parsed_data:
        parser.save_parsed_data(all_parsed_data, output_dir)
        
        print(f"\\n=== OVERALL SUMMARY ===")
        for key, statements in all_parsed_data.items():
            print(f"{key}: {len(statements)} statements")
    else:
        print("No statements processed successfully")

if __name__ == "__main__":
    main()
