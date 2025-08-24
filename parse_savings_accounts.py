#!/usr/bin/env python3
"""
Savings/Salary Account Statement Parser
Parses Kotak and SBI savings account PDFs with enhanced features
"""

import os
import re
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from pdf_statement_parser import ImprovedPDFParser

@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    type: str
    balance: Optional[float] = None
    reference: Optional[str] = None
    merchant_category: Optional[str] = None
    reward_points: int = 0

@dataclass
class AccountMetadata:
    crn: Optional[str] = None
    ifsc: Optional[str] = None
    micr: Optional[str] = None
    address: Optional[str] = None
    branch: Optional[str] = None

@dataclass
class StatementSummary:
    account_type: str
    bank: str
    account_number: str
    statement_period: dict
    transactions: List[Transaction]
    account_metadata: Optional[AccountMetadata] = None
    total_credits: float = 0.0
    total_debits: float = 0.0
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None

def extract_kotak_savings_transactions(text: str) -> List[Transaction]:
    """Extract Kotak savings account transactions using precise fixed-width column parsing"""
    transactions = []
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a new transaction using regex
        match = re.match(r'(\d+)\s+(\d{2}\s+\w{3}\s+\d{4})\s+(\d{2}\s+\w{3}\s+\d{4})\s+(.+)', line)
        if match:
            serial, txn_date, value_date, rest_of_line = match.groups()
            
            # Extract amount and balance from the end
            amounts = re.findall(r'([\+\-]?[\d,]+\.\d{2})', rest_of_line)
            if len(amounts) >= 2:
                amount_str = amounts[-2]
                balance_str = amounts[-1]
                
                # Remove amounts from rest_of_line to get description + reference
                desc_and_ref = rest_of_line
                for amt in amounts[-2:]:
                    desc_and_ref = desc_and_ref.replace(amt, '', 1)
                desc_and_ref = desc_and_ref.strip()
                
                # Split at position 56 (where IMPS- starts) - description ends at ~56, reference starts at ~56
                if len(desc_and_ref) > 30:  # Ensure we have enough content
                    # Find the boundary more precisely - look for common reference patterns
                    boundary_patterns = [r'IMPS-', r'NACHCR', r'\d{12}']
                    boundary_pos = len(desc_and_ref)  # Default to end
                    
                    for pattern in boundary_patterns:
                        match_pos = re.search(pattern, desc_and_ref)
                        if match_pos:
                            boundary_pos = match_pos.start()
                            break
                    
                    description = desc_and_ref[:boundary_pos].strip()
                    reference = desc_and_ref[boundary_pos:].strip()
                else:
                    description = desc_and_ref
                    reference = ""
                
                # Collect continuation lines using precise column positions
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    
                    # Stop if next line starts a new transaction (serial number + date pattern) or is footer
                    if re.match(r'^\d+\s+\d{2}\s+\w{3}\s+\d{4}', next_line) or 'Statement generated' in next_line:
                        break
                    
                    # For continuation lines, extract from precise column positions
                    if next_line.strip():  # Non-empty line
                        # Check if line has time prefix (like "09:33 PM")
                        time_match = re.match(r'(\d{2}:\d{2}\s+[AP]M)\s+(.+)', next_line)
                        if time_match:
                            time_part, remaining = time_match.groups()
                            # Split remaining into description and reference
                            # Look for numeric reference at the end
                            parts = remaining.split()
                            if len(parts) >= 2 and parts[-1].isdigit():
                                # Last part is reference number
                                ref_num = parts[-1]
                                desc_continuation = ' '.join(parts[:-1])
                                description += desc_continuation  # No space
                                if reference and reference.endswith('-'):  # Append to existing reference like "IMPS-"
                                    reference = reference + ref_num
                                elif not reference:  # No existing reference
                                    reference = ref_num
                            else:
                                # All is description
                                description += remaining
                        else:
                            # Regular continuation line - all description
                            desc_part = next_line.strip()
                            if desc_part:
                                description += desc_part
                    
                    j += 1
                
                try:
                    # Convert date format
                    date_obj = datetime.strptime(txn_date, '%d %b %Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    # Determine credit/debit from + or - sign
                    is_credit = amount_str.startswith('+')
                    amount_value = float(amount_str.replace('+', '').replace('-', '').replace(',', ''))
                    balance_value = float(balance_str.replace(',', ''))
                    
                    # Clean up reference (set to None if empty)
                    ref_clean = reference.strip() if reference.strip() else None
                    
                    transaction = Transaction(
                        date=formatted_date,
                        description=description.strip(),
                        amount=amount_value,
                        type='credit' if is_credit else 'debit',
                        balance=balance_value,
                        reference=ref_clean,
                        merchant_category=None,
                        reward_points=0
                    )
                    transactions.append(transaction)
                    
                except Exception as e:
                    print(f"Error parsing Kotak transaction: {line} - {e}")
                
                i = j - 1  # Move to the line before next transaction
        
        i += 1
    
    return transactions

def extract_kotak_account_metadata(text: str) -> AccountMetadata:
    """Extract Kotak account metadata"""
    metadata = AccountMetadata()
    lines = text.split('\n')
    
    # CRN XXXXXX451
    crn_match = re.search(r'CRN\s+(\w+)', text)
    if crn_match:
        metadata.crn = crn_match.group(1)
    
    # IFSC KKBK0008042
    ifsc_match = re.search(r'IFSC\s+(\w+)', text)
    if ifsc_match:
        metadata.ifsc = ifsc_match.group(1)
    
    # MICR 560485024
    micr_match = re.search(r'MICR\s+(\d+)', text)
    if micr_match:
        metadata.micr = micr_match.group(1)
    
    # Branch Bangalore-Whitefield
    branch_match = re.search(r'Branch\s+(.+)', text)
    if branch_match:
        metadata.branch = branch_match.group(1).strip()
    
    # Extract address - lines 5-8 contain the address
    address_parts = []
    for i, line in enumerate(lines):
        if i >= 5 and i <= 8:  # Lines 5-8 contain address
            line = line.strip()
            if line and not line.startswith('#'):
                # Clean up IFSC and MICR from address lines
                clean_line = re.sub(r'\s*IFSC\s+\w+|\s*MICR\s+\d+', '', line).strip()
                if clean_line:
                    address_parts.append(clean_line)
    
    if address_parts:
        metadata.address = '\n'.join(address_parts)
    
    return metadata

def extract_sbi_savings_transactions(pdf_path: str) -> List[Transaction]:
    """Extract SBI savings account transactions using table structure detection from all pages"""
    transactions = []
    
    try:
        import pdfplumber
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract table with proper settings
                table = page.extract_table({
                    'vertical_strategy': 'lines',
                    'horizontal_strategy': 'lines', 
                    'snap_tolerance': 3,
                    'join_tolerance': 3
                })
                
                if table and len(table) > 0:
                    # Process all rows (skip header row if it's the first page)
                    start_row = 1 if page_num == 0 else 0  # Skip header only on first page
                    
                    for row in table[start_row:]:
                        if len(row) >= 7 and row[0]:  # Ensure we have all columns and a date
                            txn_date_raw = row[0].strip() if row[0] else ""
                            value_date_raw = row[1].strip() if row[1] else ""
                            description = row[2].strip() if row[2] else ""
                            reference = row[3].strip() if row[3] else ""
                            debit = row[4].strip() if row[4] else ""
                            credit = row[5].strip() if row[5] else ""
                            balance = row[6].strip() if row[6] else ""
                            
                            # Skip empty rows or header rows
                            if not txn_date_raw or not balance or not any(char.isdigit() for char in txn_date_raw):
                                continue
                            
                            # Clean up date (handle multi-line dates like "13 Apr\n2025")
                            txn_date_clean = re.sub(r'\s+', ' ', txn_date_raw).strip()
                            
                            # Determine amount and type
                            if debit:
                                amount_str = debit
                                txn_type = 'debit'
                            elif credit:
                                amount_str = credit
                                txn_type = 'credit'
                            else:
                                continue  # Skip if no amount
                            
                            # Clean up multi-line fields (remove spaces between lines)
                            description_clean = re.sub(r'\s+', '', description).strip()
                            reference_clean = re.sub(r'\s+', '', reference).strip() if reference else None
                            
                            try:
                                # Parse date
                                date_obj = datetime.strptime(txn_date_clean, '%d %b %Y')
                                formatted_date = date_obj.strftime('%Y-%m-%d')
                                
                                # Parse amounts
                                amount_value = float(amount_str.replace(',', ''))
                                balance_value = float(balance.replace(',', ''))
                                
                                transaction = Transaction(
                                    date=formatted_date,
                                    description=description_clean,
                                    amount=amount_value,
                                    type=txn_type,
                                    balance=balance_value,
                                    reference=reference_clean,
                                    merchant_category=None,
                                    reward_points=0
                                )
                                transactions.append(transaction)
                                
                            except Exception as e:
                                print(f"Error parsing SBI table row on page {page_num+1}: {row} - {e}")
                                continue
            
    except ImportError:
        print("pdfplumber not available, falling back to text parsing")
        # Fallback to previous text-based parsing
        return extract_sbi_savings_transactions_text("")
    except Exception as e:
        print(f"Error with table extraction: {e}, falling back to text parsing")
        return extract_sbi_savings_transactions_text("")
    
    return transactions

def extract_sbi_savings_transactions_text(text: str) -> List[Transaction]:
    """Fallback text-based SBI parser"""
    transactions = []
    lines = text.split('\n')
    
    # SBI Column positions based on header analysis:
    # Txn Date Value Description Ref No./Cheque Debit Credit Balance
    # 0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
    # Description: positions 15-27
    # Ref No./Cheque: positions 27-42
    # Amounts: positions 42+
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for transaction patterns (lines with amounts)
        amounts = re.findall(r'([\d,]+\.\d{2})', line)
        if len(amounts) >= 2:  # Transaction line must have at least 2 amounts
            balance_str = amounts[-1]
            amount_str = amounts[-2]
            
            # Determine if it's full date or partial date transaction
            full_date_match = re.match(r'(\d{1,2}\s+\w{3}\s+\d{4})\s+(\d{1,2}\s+\w{3}\s+\d{4})\s+(.+)', line)
            partial_date_match = re.match(r'(\d{1,2}\s+\w{3})\s+(\d{1,2}\s+\w{3})\s+(.+)', line)
            
            if full_date_match:
                # Full date transaction
                txn_date, value_date, rest_of_line = full_date_match.groups()
                year = "2025"  # Extract from txn_date if needed
            elif partial_date_match:
                # Partial date transaction - need to get year from next line
                partial_txn_date, partial_value_date, rest_of_line = partial_date_match.groups()
                
                # Look for year in next line
                year = "2025"  # Default year
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    year_match = re.match(r'(\d{4})\s+\d{4}', next_line)
                    if year_match:
                        year = year_match.group(1)
                
                txn_date = f"{partial_txn_date} {year}"
                value_date = f"{partial_value_date} {year}"
            else:
                # Skip if we can't parse the date
                i += 1
                continue
            
            # Remove amounts from rest_of_line to get description + reference
            desc_and_ref = rest_of_line
            for amt in amounts[-2:]:
                desc_and_ref = desc_and_ref.replace(amt, '', 1)
            desc_and_ref = desc_and_ref.strip()
            
            # Use fixed-width column parsing to separate description and reference
            # Find where the description should end (around position 27-42 range)
            # Look for common reference patterns to find the boundary
            description = desc_and_ref
            reference = ""
            
            # Split at common reference patterns
            ref_patterns = [
                r'(TRANSFER TO)',
                r'(TRANSFER FROM)', 
                r'(\d{5,})',  # Long numbers
            ]
            
            for pattern in ref_patterns:
                match = re.search(pattern, description)
                if match:
                    split_pos = match.start()
                    reference = description[split_pos:].strip()
                    description = description[:split_pos].strip()
                    break
            
            # Collect continuation lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                
                # Stop if next line is a transaction line (has amounts) or is empty
                next_amounts = re.findall(r'([\d,]+\.\d{2})', next_line)
                if len(next_amounts) >= 2 or not next_line.strip():
                    break
                
                # Process continuation line
                next_line = next_line.strip()
                if next_line:
                    # Skip year continuation lines (like "2025 2025")
                    if re.match(r'^\d{4}\s+\d{4}', next_line):
                        # Extract description part after years using column positions
                        desc_part = re.sub(r'^\d{4}\s+\d{4}\s*', '', next_line)
                        if len(desc_part) > 15:  # Has content in description column
                            # Description column: positions ~15-27 in continuation
                            desc_continuation = desc_part[:12].strip()  # ~12 chars for description
                            ref_continuation = desc_part[12:].strip()   # Rest for reference
                            
                            if desc_continuation:
                                description += desc_continuation
                            if ref_continuation and not reference:
                                reference = ref_continuation
                        elif desc_part:
                            description += desc_part
                    elif re.match(r'^\d{5,}$', next_line):
                        # Pure reference number
                        if not reference:
                            reference = next_line
                    else:
                        # Regular description continuation
                        description += next_line
                
                j += 1
            
            # Determine transaction type
            txn_type = 'debit' if any(word in description.upper() for word in ['WITHDRAWAL', 'CASH CHEQUE']) or 'TRANSFER TO' in reference else 'credit'
            
            try:
                # Convert date format
                date_obj = datetime.strptime(txn_date, '%d %b %Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                
                amount_value = float(amount_str.replace(',', ''))
                balance_value = float(balance_str.replace(',', ''))
                
                # Clean up reference (set to None if empty)
                ref_clean = reference.strip() if reference.strip() else None
                
                transaction = Transaction(
                    date=formatted_date,
                    description=description.strip(),
                    amount=amount_value,
                    type=txn_type,
                    balance=balance_value,
                    reference=ref_clean,
                    merchant_category=None,
                    reward_points=0
                )
                transactions.append(transaction)
                
            except Exception as e:
                print(f"Error parsing SBI transaction: {line} - {e}")
            
            i = j - 1  # Move to the line before next transaction
        
        i += 1
    
    return transactions
    transactions = []
    lines = text.split('\n')
    
    # SBI Column positions based on header analysis:
    # Txn Date Value Description Ref No./Cheque Debit Credit Balance
    # 0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
    # Description: positions 15-27
    # Ref No./Cheque: positions 27-42
    # Amounts: positions 42+
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for transaction patterns (lines with amounts)
        amounts = re.findall(r'([\d,]+\.\d{2})', line)
        if len(amounts) >= 2:  # Transaction line must have at least 2 amounts
            balance_str = amounts[-1]
            amount_str = amounts[-2]
            
            # Determine if it's full date or partial date transaction
            full_date_match = re.match(r'(\d{1,2}\s+\w{3}\s+\d{4})\s+(\d{1,2}\s+\w{3}\s+\d{4})\s+(.+)', line)
            partial_date_match = re.match(r'(\d{1,2}\s+\w{3})\s+(\d{1,2}\s+\w{3})\s+(.+)', line)
            
            if full_date_match:
                # Full date transaction
                txn_date, value_date, rest_of_line = full_date_match.groups()
                year = "2025"  # Extract from txn_date if needed
            elif partial_date_match:
                # Partial date transaction - need to get year from next line
                partial_txn_date, partial_value_date, rest_of_line = partial_date_match.groups()
                
                # Look for year in next line
                year = "2025"  # Default year
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    year_match = re.match(r'(\d{4})\s+\d{4}', next_line)
                    if year_match:
                        year = year_match.group(1)
                
                txn_date = f"{partial_txn_date} {year}"
                value_date = f"{partial_value_date} {year}"
            else:
                # Skip if we can't parse the date
                i += 1
                continue
            
            # Remove amounts from rest_of_line to get description + reference
            desc_and_ref = rest_of_line
            for amt in amounts[-2:]:
                desc_and_ref = desc_and_ref.replace(amt, '', 1)
            desc_and_ref = desc_and_ref.strip()
            
            # Use fixed-width column parsing to separate description and reference
            # Find where the description should end (around position 27-42 range)
            # Look for common reference patterns to find the boundary
            description = desc_and_ref
            reference = ""
            
            # Split at common reference patterns
            ref_patterns = [
                r'(TRANSFER TO)',
                r'(TRANSFER FROM)', 
                r'(\d{5,})',  # Long numbers
            ]
            
            for pattern in ref_patterns:
                match = re.search(pattern, description)
                if match:
                    split_pos = match.start()
                    reference = description[split_pos:].strip()
                    description = description[:split_pos].strip()
                    break
            
            # Collect continuation lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                
                # Stop if next line is a transaction line (has amounts) or is empty
                next_amounts = re.findall(r'([\d,]+\.\d{2})', next_line)
                if len(next_amounts) >= 2 or not next_line.strip():
                    break
                
                # Process continuation line
                next_line = next_line.strip()
                if next_line:
                    # Skip year continuation lines (like "2025 2025")
                    if re.match(r'^\d{4}\s+\d{4}', next_line):
                        # Extract description part after years using column positions
                        desc_part = re.sub(r'^\d{4}\s+\d{4}\s*', '', next_line)
                        if len(desc_part) > 15:  # Has content in description column
                            # Description column: positions ~15-27 in continuation
                            desc_continuation = desc_part[:12].strip()  # ~12 chars for description
                            ref_continuation = desc_part[12:].strip()   # Rest for reference
                            
                            if desc_continuation:
                                description += desc_continuation
                            if ref_continuation and not reference:
                                reference = ref_continuation
                        elif desc_part:
                            description += desc_part
                    elif re.match(r'^\d{5,}$', next_line):
                        # Pure reference number
                        if not reference:
                            reference = next_line
                    else:
                        # Regular description continuation
                        description += next_line
                
                j += 1
            
            # Determine transaction type
            txn_type = 'debit' if any(word in description.upper() for word in ['WITHDRAWAL', 'CASH CHEQUE']) or 'TRANSFER TO' in reference else 'credit'
            
            try:
                # Convert date format
                date_obj = datetime.strptime(txn_date, '%d %b %Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                
                amount_value = float(amount_str.replace(',', ''))
                balance_value = float(balance_str.replace(',', ''))
                
                # Clean up reference (set to None if empty)
                ref_clean = reference.strip() if reference.strip() else None
                
                transaction = Transaction(
                    date=formatted_date,
                    description=description.strip(),
                    amount=amount_value,
                    type=txn_type,
                    balance=balance_value,
                    reference=ref_clean,
                    merchant_category=None,
                    reward_points=0
                )
                transactions.append(transaction)
                
            except Exception as e:
                print(f"Error parsing SBI transaction: {line} - {e}")
            
            i = j - 1  # Move to the line before next transaction
        
        i += 1
    
    return transactions


def extract_canara_savings_transactions(pdf_path: str) -> List[Transaction]:
    """Extract Canara savings account transactions using table structure"""
    transactions = []
    
    try:
        import pdfplumber
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                table = page.extract_table()
                
                if table and len(table) > 0:
                    # For first page, look for transaction rows in the large table
                    if page_num == 0:
                        start_row = 0
                        # Find transactions by looking for date patterns in first column
                        for i, row in enumerate(table):
                            if (row and len(row) >= 8 and row[0] and 
                                any(c.isdigit() for c in str(row[0])) and '-' in str(row[0])):
                                # This looks like a transaction row
                                pass  # Process all transaction-like rows
                            else:
                                continue
                    else:
                        # Skip header row on subsequent pages
                        start_row = 1 if table[0] and 'Txn Date' in str(table[0][0]) else 0
                    
                    for row in table[start_row:]:
                        if len(row) >= 8 and row[0]:
                            # Check if this is a transaction row (has date pattern)
                            if not (any(c.isdigit() for c in str(row[0])) and '-' in str(row[0])):
                                continue
                                
                            txn_date_raw = row[0].strip() if row[0] else ""
                            value_date_raw = row[1].strip() if row[1] else ""
                            reference = row[2].strip() if row[2] else ""
                            description = row[3].strip() if row[3] else ""
                            branch_code = row[4].strip() if row[4] else ""
                            debit = row[5].strip() if row[5] else ""
                            credit = row[6].strip() if row[6] else ""
                            # Balance can be in column 7 or 8 depending on table structure
                            balance = row[8].strip() if len(row) > 8 and row[8] else (row[7].strip() if row[7] else "")
                            
                            # Clean description - remove \n and join lines without space
                            description = re.sub(r'\s*\n\s*', '', description)
                            
                            # Skip empty rows
                            if not txn_date_raw or not balance:
                                continue
                            
                            # Extract date part (DD-MM-YYYY from "30-06-2022 16:17:05")
                            txn_date_clean = txn_date_raw.split()[0] if ' ' in txn_date_raw else txn_date_raw
                            
                            # Determine amount and type
                            if debit and any(c.isdigit() for c in debit):
                                amount_str = debit
                                txn_type = 'debit'
                            elif credit and any(c.isdigit() for c in credit):
                                amount_str = credit
                                txn_type = 'credit'
                            else:
                                continue
                            
                            try:
                                # Parse date (DD-MM-YYYY format)
                                date_obj = datetime.strptime(txn_date_clean, '%d-%m-%Y')
                                formatted_date = date_obj.strftime('%Y-%m-%d')
                                
                                # Clean amounts - remove non-numeric parts
                                amount_clean = re.sub(r'[^\d,.]', '', amount_str)
                                balance_clean = re.sub(r'[^\d,.]', '', balance)
                                
                                amount_value = float(amount_clean.replace(',', ''))
                                balance_value = float(balance_clean.replace(',', ''))
                                
                                transaction = Transaction(
                                    date=formatted_date,
                                    description=description,
                                    amount=amount_value,
                                    type=txn_type,
                                    balance=balance_value,
                                    reference=reference
                                )
                                transactions.append(transaction)
                                
                            except Exception as e:
                                print(f"Error parsing Canara row on page {page_num+1}: {e}")
                                continue
            
    except ImportError:
        print("pdfplumber not available")
        return []
    except Exception as e:
        print(f"Error with Canara extraction: {e}")
        return []
    
    return transactions

def extract_canara_account_metadata(text: str) -> AccountMetadata:
    """Extract Canara account metadata from first page"""
    metadata = AccountMetadata()
    
    # Customer Id 118261147 (map to CRN)
    crn_match = re.search(r'Customer Id\s+(\d+)', text)
    if crn_match:
        metadata.crn = crn_match.group(1)
    
    # IFSC Code CNRB0002466
    ifsc_match = re.search(r'IFSC Code\s+([A-Z0-9]+)', text)
    if ifsc_match:
        metadata.ifsc = ifsc_match.group(1)
    
    # MICR Code 756015002
    micr_match = re.search(r'MICR Code\s+(\d+)', text)
    if micr_match:
        metadata.micr = micr_match.group(1)
    
    # Branch Name BALASORE (extract only the name, not "MICR C")
    branch_match = re.search(r'Branch Name\s+([A-Z]+)', text)
    if branch_match:
        metadata.branch = branch_match.group(1)
    
    # Extract address from top left (lines 1-5)
    lines = text.split('\n')
    address_parts = []
    for i in range(1, 6):  # Lines 1-5 contain address
        if i < len(lines):
            line = lines[i].strip()
            if line and not any(x in line for x in ['Account Statement', 'Account Holders']):
                address_parts.append(line)
    
    if address_parts:
        metadata.address = '\n'.join(address_parts)
    
    return metadata

def extract_sbi_account_metadata(text: str) -> AccountMetadata:
    """Extract SBI account metadata"""
    metadata = AccountMetadata()
    
    # CIF No. :(cid:9)90984592586 (CRN equivalent)
    cif_match = re.search(r'CIF No\.?\s*:.*?(\d{10,})', text)
    if cif_match:
        metadata.crn = cif_match.group(1)
    
    # IFS Code :SBIN0006933
    ifsc_match = re.search(r'IFS Code\s*:.*?([A-Z0-9]{11})', text)
    if ifsc_match:
        metadata.ifsc = ifsc_match.group(1)
    
    # MICR Code :(cid:9)756002004
    micr_match = re.search(r'MICR Code\s*:.*?(\d{9})', text)
    if micr_match:
        metadata.micr = micr_match.group(1)
    
    # Branch :(cid:9)MOTIGANJ EVENING BRANCH
    branch_match = re.search(r'Branch\s*:.*?([A-Z\s]+BRANCH)', text)
    if branch_match:
        metadata.branch = branch_match.group(1).strip()
    
    # Extract address from first page
    lines = text.split('\n')
    address_parts = []
    for i, line in enumerate(lines[:15]):
        if 'Mr. JYOTIRMAY SETHI' in line or 'S/O,Sashikanta Sethi' in line:
            # Collect address lines after name
            for j in range(i+1, min(i+5, len(lines))):
                addr_line = lines[j].strip()
                if addr_line and not any(x in addr_line for x in ['Date :', 'Account Number', 'CIF No', 'IFS Code']):
                    addr_clean = re.sub(r'\(cid:\d+\)', '', addr_line).strip()
                    if addr_clean:
                        address_parts.append(addr_clean)
            break
    
    if address_parts:
        metadata.address = '\n'.join(address_parts)
    
    return metadata


    """Extract SBI account metadata"""
    metadata = AccountMetadata()
    
    # IFS Code :SBIN0006933
    ifsc_match = re.search(r'IFS Code\s*:\s*(\w+)', text)
    if ifsc_match:
        metadata.ifsc = ifsc_match.group(1)
    
    # MICR Code :(cid:9)756002004
    micr_match = re.search(r'MICR Code\s*:.*?(\d+)', text)
    if micr_match:
        metadata.micr = micr_match.group(1)
    
    # Branch :(cid:9)MOTIGANJ EVENING BRANCH
    branch_match = re.search(r'Branch\s*:.*?([A-Z\s]+BRANCH)', text)
    if branch_match:
        metadata.branch = branch_match.group(1).strip()
    
    # Extract address from the beginning
    lines = text.split('\n')
    address_parts = []
    for i, line in enumerate(lines[:10]):
        if 'S/O,Sashikanta Sethi' in line:
            # Collect address lines
            for j in range(i, min(i+5, len(lines))):
                addr_line = lines[j].strip()
                if addr_line and not any(x in addr_line for x in ['Date :', 'Account Number', 'Account Description']):
                    # Clean up address line
                    addr_clean = re.sub(r'\(cid:\d+\)', '', addr_line).strip()
                    if addr_clean and addr_clean not in ['Mr. JYOTIRMAY SETHI']:
                        address_parts.append(addr_clean)
            break
    
    if address_parts:
        metadata.address = '\n'.join(address_parts)
    
    return metadata

def extract_account_info(text: str, bank: str) -> dict:
    """Extract account number and statement period"""
    account_info = {"account_number": "", "statement_period": {"start": "", "end": ""}}
    
    if bank.lower() == 'kotak':
        # Account # 2449511321 SAVINGS
        match = re.search(r'Account # (\d+)', text)
        if match:
            account_info["account_number"] = match.group(1)
        
        # Look for statement period right after "Account Statement"
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'Account Statement' in line and i+2 < len(lines):
                # Check next few lines for date range
                for j in range(i+1, min(i+4, len(lines))):
                    date_match = re.search(r'(\d{2}\s+\w{3}\s+\d{4})\s+-\s+(\d{2}\s+\w{3}\s+\d{4})', lines[j])
                    if date_match:
                        start_date = datetime.strptime(date_match.group(1), '%d %b %Y').strftime('%Y-%m-%d')
                        end_date = datetime.strptime(date_match.group(2), '%d %b %Y').strftime('%Y-%m-%d')
                        account_info["statement_period"] = {"start": start_date, "end": end_date}
                        break
                break
    
    elif bank.lower() == 'sbi':
        # Account Number :(cid:9)00000041083981739
        match = re.search(r'Account Number\s*:.*?(\d{11,})', text)
        if match:
            account_info["account_number"] = match.group(1)
            print(f"Found SBI account number: {match.group(1)}")
        
        # Account Statement from 30 Mar 2025 to 25 Jul 2025
        match = re.search(r'from\s+(\d{1,2}\s+\w{3}\s+\d{4})\s+to\s+(\d{1,2}\s+\w{3}\s+\d{4})', text)
        if match:
            start_date = datetime.strptime(match.group(1), '%d %b %Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(match.group(2), '%d %b %Y').strftime('%Y-%m-%d')
            account_info["statement_period"] = {"start": start_date, "end": end_date}
        
        # Balance as on 30 Mar 2025 :(cid:9)9,09,371.58
        balance_match = re.search(r'Balance as on.*?([0-9,]+\.\d{2})', text)
        if balance_match:
            account_info["opening_balance"] = float(balance_match.group(1).replace(',', ''))
    
    elif bank.lower() == 'canara':
        # Account Number 8517101005159
        match = re.search(r'Account Number\s+(\d+)', text)
        if match:
            account_info["account_number"] = match.group(1)
        
        # Searched By From 13 Jun 2022 To 22 Jul 2025 (statement period)
        match = re.search(r'From\s+(\d{1,2}\s+\w{3}\s+\d{4})\s+To\s+(\d{1,2}\s+\w{3}\s+\d{4})', text)
        if match:
            try:
                start_date = datetime.strptime(match.group(1), '%d %b %Y').strftime('%Y-%m-%d')
                end_date = datetime.strptime(match.group(2), '%d %b %Y').strftime('%Y-%m-%d')
                account_info["statement_period"] = {"start": start_date, "end": end_date}
            except:
                pass
        
        # Opening Balance Rs. 872.62
        balance_match = re.search(r'Opening Balance Rs\.\s+([0-9,]+\.\d{2})', text)
        if balance_match:
            account_info["opening_balance"] = float(balance_match.group(1).replace(',', ''))
    
    return account_info

def main():
    """Parse savings account statements"""
    parser = ImprovedPDFParser()
    
    base_dir = "/Users/jmysethi/Documents/Finance/Financial Records"
    output_dir = "/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/statements/saving"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("Processing savings/salary account statements...")
    
    # Define savings account directories
    savings_dirs = [
        "Saving:Salary/Kotak",
        "Saving:Salary/SBI",
        "Saving:Salary/Canara"
    ]
    
    # Process all PDF files in each directory
    for savings_dir in savings_dirs:
        full_dir_path = os.path.join(base_dir, savings_dir)
        if not os.path.exists(full_dir_path):
            print(f"Directory not found: {full_dir_path}")
            continue
            
        bank_name = os.path.basename(savings_dir)  # Extract bank name from path
        
        # Get all PDF files in the directory
        pdf_files = [f for f in os.listdir(full_dir_path) if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in {savings_dir}")
            continue
            
        for pdf_file in pdf_files:
            file_path = os.path.join(full_dir_path, pdf_file)
            
            print(f"\nProcessing {bank_name}: {pdf_file}")
            
            try:
                text = parser.extract_text_from_pdf(file_path)
                
                # Extract transactions based on bank
                if bank_name.lower() == 'kotak':
                    transactions = extract_kotak_savings_transactions(text)
                    metadata = extract_kotak_account_metadata(text)
                elif bank_name.lower() == 'sbi':
                    transactions = extract_sbi_savings_transactions(file_path)
                    metadata = extract_sbi_account_metadata(text)
                elif bank_name.lower() == 'canara':
                    transactions = extract_canara_savings_transactions(file_path)
                    metadata = extract_canara_account_metadata(text)

                else:
                    transactions = []
                    metadata = None
                
                # Extract account info
                account_info = extract_account_info(text, bank_name)
                
                # Calculate totals
                total_credits = sum(t.amount for t in transactions if t.type == 'credit')
                total_debits = sum(t.amount for t in transactions if t.type == 'debit')
                
                # Create statement summary
                summary = StatementSummary(
                    account_type="savings",
                    bank=bank_name,
                    account_number=account_info["account_number"],
                    statement_period=account_info["statement_period"],
                    transactions=transactions,
                    account_metadata=metadata,
                    total_credits=total_credits,
                    total_debits=total_debits,
                    opening_balance=account_info.get("opening_balance") or (transactions[0].balance - transactions[0].amount if transactions else None),
                    closing_balance=transactions[-1].balance if transactions else None
                )
                
                print(f"Extracted {len(transactions)} transactions")
                print(f"Credits: ₹{total_credits:,.2f}")
                print(f"Debits: ₹{total_debits:,.2f}")
                if metadata:
                    print(f"Account metadata: CRN={metadata.crn}, IFSC={metadata.ifsc}, MICR={metadata.micr}")
                
                # Save to JSON
                file_basename = os.path.splitext(pdf_file)[0]
                filename = f"statement_data_{bank_name}_savings_{file_basename}_202508.json"
                filepath = os.path.join(output_dir, filename)
                
                # Convert to dict for JSON serialization
                output_data = asdict(summary)
                
                with open(filepath, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                
                print(f"Saved to {filepath}")
                
            except Exception as e:
                print(f"Error processing {bank_name} - {pdf_file}: {e}")
                total_credits = sum(t.amount for t in transactions if t.type == 'credit')
                total_debits = sum(t.amount for t in transactions if t.type == 'debit')
            
                # Create statement summary
                summary = StatementSummary(
                    account_type="savings",
                    bank=bank_name,
                    account_number=account_info["account_number"],
                    statement_period=account_info["statement_period"],
                    transactions=transactions,
                    account_metadata=metadata,
                    total_credits=total_credits,
                    total_debits=total_debits,
                    opening_balance=account_info.get("opening_balance") or (transactions[0].balance - transactions[0].amount if transactions else None),
                    closing_balance=transactions[-1].balance if transactions else None
                )
                
                print(f"Extracted {len(transactions)} transactions")
                print(f"Credits: ₹{total_credits:,.2f}")
                print(f"Debits: ₹{total_debits:,.2f}")
                if metadata:
                    print(f"Account metadata: CRN={metadata.crn}, IFSC={metadata.ifsc}, MICR={metadata.micr}")
                
                # Save to JSON
                file_basename = os.path.splitext(os.path.basename(file_path))[0]
                filename = f"statement_data_{bank_name}_savings_{file_basename}_202508.json"
                filepath = os.path.join(output_dir, filename)
                
                # Convert to dict for JSON serialization
                output_data = asdict(summary)
                
                with open(filepath, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                
                print(f"Saved to {filepath}")
                
            except Exception as e:
                print(f"Error processing {bank_name} - {os.path.basename(file_path)}: {e}")

if __name__ == "__main__":
    main()
