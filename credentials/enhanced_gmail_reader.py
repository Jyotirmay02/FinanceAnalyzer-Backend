from __future__ import print_function
import os.path
import re
import base64
import json
import sys
from datetime import datetime
from typing import List, Dict, Optional
import google.auth.transport.requests
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transaction_models import TransactionFactory, transaction_to_dict

# If modifying scopes, delete the token.json file
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TOKEN_PATH = "token.json"  # Same as original - in root directory
CREDENTIALS_PATH = "/Users/jmysethi/Downloads/client_secret_885429144379-als8fusnv1vqdo3oosna9j3glp77ckm5.apps.googleusercontent.com.json"

class GmailTransactionReader:
    def __init__(self):
        self.service = None
        self.creds = None
        
    def authenticate(self) -> Credentials:
        """Authenticate with Gmail API"""
        creds = None

        # Load existing token if available
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        # If no valid creds, ask user to login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(google.auth.transport.requests.Request())
                    print("✅ Token refreshed successfully")
                except RefreshError:
                    print("⚠️ Refresh token expired, logging in again…")
                    creds = None
            
            if not creds:
                print("🔐 Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=8080)
                print("✅ Authentication successful")

            # Save creds for next run
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
            print(f"💾 Token saved to {TOKEN_PATH}")

        self.creds = creds
        self.service = build('gmail', 'v1', credentials=creds)
        return creds

    def get_email_content(self, message_id: str) -> str:
        """Extract text content from email message"""
        msg_data = self.service.users().messages().get(userId='me', id=message_id).execute()
        payload = msg_data['payload']
        parts = payload.get('parts', [])
        data = ""

        # Function to extract text from HTML
        def extract_text_from_html(html_content):
            import re
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_content)
            # Replace HTML entities
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            # Clean up whitespace
            text = ' '.join(text.split())
            return text

        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    html_data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    data = extract_text_from_html(html_data)
                    break
        else:
            if 'data' in payload['body']:
                if payload.get('mimeType') == 'text/html':
                    html_data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                    data = extract_text_from_html(html_data)
                else:
                    data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        return data

    def parse_hsbc_transaction(self, email_content: str) -> Optional[Dict]:
        """Parse HSBC transaction email content"""
        transaction = {}
        
        # Check if it's a credit transaction
        credit_match = re.search(r'received credits of ₹\s*([\d,]+\.\d{2}) on your HSBC credit card ending with (\d{4}) on (\d{1,2}/\d{1,2}/\d{4})', email_content, re.IGNORECASE)
        
        if credit_match:
            # Credit transaction
            transaction['amount'] = float(credit_match.group(1).replace(',', ''))
            transaction['card_last4'] = credit_match.group(2)
            transaction['date'] = credit_match.group(3)
            transaction['merchant'] = 'Credit Adjustment'
            transaction['transaction_type'] = 'credit'
            transaction['time'] = None
            
            # Convert date format from DD/MM/YYYY to YYYY-MM-DD
            try:
                from datetime import datetime
                parsed_date = datetime.strptime(transaction['date'], '%d/%m/%Y')
                transaction['date'] = parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                pass
                
        else:
            # Regular debit transaction patterns
            patterns = {
                'card_last4': r'ending with (\d{4})',
                'amount': r'INR\s*([\d,]+\.\d{2})',
                'merchant': r'payment to ([A-Z0-9 &\-\.]+?) on',
                'date': r'on (\d{1,2} \w+ \d{4}) at',
                'time': r'at (\d{2}:\d{2})'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, email_content, re.IGNORECASE)
                transaction[key] = match.group(1) if match else None
            
            # Detect transaction type from email content
            if 'purchase transaction' in email_content.lower():
                transaction['transaction_type'] = 'purchase'
            elif 'payment' in email_content.lower():
                transaction['transaction_type'] = 'payment'
            else:
                transaction['transaction_type'] = 'debit'
                
            # Parse date to standard format - handle both formats
            if transaction.get('date'):
                try:
                    # Try short month format first (Aug)
                    from datetime import datetime
                    parsed_date = datetime.strptime(transaction['date'], '%d %b %Y')
                    transaction['date'] = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    try:
                        # Try full month format (August)
                        parsed_date = datetime.strptime(transaction['date'], '%d %B %Y')
                        transaction['date'] = parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        pass
        
        # Only return if we have essential fields
        if transaction.get('amount') and (transaction.get('merchant') or transaction.get('transaction_type') == 'credit'):
            # Clean up amount (remove commas)
            if transaction['amount']:
                transaction['amount'] = float(str(transaction['amount']).replace(',', ''))
                
            # Clean up merchant name
            if transaction.get('merchant'):
                transaction['merchant'] = transaction['merchant'].strip()
            
            # Standardize transaction_type to credit/debit
            if transaction.get('transaction_type') == 'credit':
                transaction['transaction_type'] = 'credit'
            else:
                transaction['transaction_type'] = 'debit'
                    
            transaction['bank'] = 'HSBC'
            
            # Move source and email_id to metadata
            transaction['metadata'] = {
                'source': 'email',
                'card_type': 'credit'
            }
            
            # Remove old fields
            if 'source' in transaction:
                del transaction['source']
            if 'card_type' in transaction:
                del transaction['card_type']
                
            return transaction
            
    def parse_kotak_transaction(self, email_content: str) -> Optional[Dict]:
        """Parse Kotak transaction email content"""
        transaction = {}
        
        # Pattern 1: Card transaction
        card_match = re.search(r'Your transaction of Rs\.([\d,]+\.\d{2}) on ([A-Z0-9\*\s]+) using Kotak Bank Debit Card XX(\d{4}) on (\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}:\d{2}).*?reference No is (\d+)', email_content, re.IGNORECASE | re.DOTALL)
        
        if card_match:
            # Extract merchant name properly
            raw_merchant = card_match.group(2).strip()
            merchant = self._clean_merchant_name(raw_merchant)
            
            transaction = {
                'amount': float(card_match.group(1).replace(',', '')),
                'merchant': merchant,
                'card_last4': card_match.group(3),
                'date': card_match.group(4),
                'time': card_match.group(5),
                'transaction_type': 'debit',
                'reference_number': card_match.group(6)
            }
            
        else:
            # Pattern 2: IMPS Debit
            imps_debit_match = re.search(r'account xx\d+ is debited for Rs\. ([\d,]+\.\d{2}) on (\d{2}-\w{3}-\d{4}) towards IMPS.*?Beneficiary Name: ([^\r\n]+).*?Beneficiary Account No: ([^\r\n]+).*?IMPS Reference No: (\d+)', email_content, re.IGNORECASE | re.DOTALL)
            
            if imps_debit_match:
                transaction = {
                    'amount': float(imps_debit_match.group(1).replace(',', '')),
                    'date': imps_debit_match.group(2),
                    'merchant': f"IMPS to {imps_debit_match.group(3).strip()}",
                    'transaction_type': 'debit',
                    'beneficiary_name': imps_debit_match.group(3).strip(),
                    'beneficiary_account': imps_debit_match.group(4).strip(),
                    'reference_number': imps_debit_match.group(5),
                    'time': None,
                    'card_last4': None
                }
                
            else:
                # Pattern 3: IMPS Credit
                imps_credit_match = re.search(r'account xx\d+ is credited by Rs\. ([\d,]+\.\d{2}) on (\d{2}-\w{3}-\d{4}) for IMPS.*?Sender Name: ([^\r\n]+).*?IMPS Reference No: (\d+)', email_content, re.IGNORECASE | re.DOTALL)
                
                if imps_credit_match:
                    sender_name = imps_credit_match.group(3).strip()
                    
                    transaction = {
                        'amount': float(imps_credit_match.group(1).replace(',', '')),
                        'date': imps_credit_match.group(2),
                        'merchant': f"IMPS from {sender_name}",
                        'transaction_type': 'credit',
                        'sender_name': sender_name,
                        'reference_number': imps_credit_match.group(4),
                        'time': None,
                        'card_last4': None
                    }
                    
                else:
                    # Pattern 4: NACH/ECS Credit
                    nach_match = re.search(r'credited with payment received via NACH/ECS.*?Remitter\s*:\s*([^\r\n]+).*?Amount:\s*Rs\.([\d,]+\.\d{2}).*?Transaction date\s*:\s*(\d{2}/\d{2}/\d{4})', email_content, re.IGNORECASE | re.DOTALL)
                    
                    if nach_match:
                        remitter = nach_match.group(1).strip()
                        employer_name = self._extract_employer_name(remitter)
                        
                        transaction = {
                            'amount': float(nach_match.group(2).replace(',', '')),
                            'merchant': f"NACH/ECS from {employer_name}",
                            'date': nach_match.group(3),
                            'transaction_type': 'credit',
                            'employer_name': employer_name,
                            'payment_type': 'NACH/ECS',
                            'remitter_code': remitter,
                            'time': None,
                            'card_last4': None
                        }
        
        # Only return if we have essential fields
        if transaction.get('amount') and transaction.get('merchant'):
            # Parse date to standard format
            if transaction.get('date'):
                try:
                    from datetime import datetime
                    # Handle DD/MM/YYYY format
                    if '/' in transaction['date']:
                        parsed_date = datetime.strptime(transaction['date'], '%d/%m/%Y')
                        transaction['date'] = parsed_date.strftime('%Y-%m-%d')
                    # Handle DD-MMM-YYYY format
                    elif '-' in transaction['date']:
                        parsed_date = datetime.strptime(transaction['date'], '%d-%b-%Y')
                        transaction['date'] = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
                    
            transaction['bank'] = 'Kotak'
            
            # Add metadata based on transaction type
            if transaction.get('card_last4'):
                transaction['metadata'] = {
                    'source': 'email',
                    'card_type': 'debit',
                    'transaction_category': 'card'
                }
            elif 'IMPS' in transaction.get('merchant', ''):
                transaction['metadata'] = {
                    'source': 'email',
                    'transaction_category': 'transfer',
                    'transfer_type': 'IMPS'
                }
            elif 'NACH' in transaction.get('merchant', ''):
                transaction['metadata'] = {
                    'source': 'email',
                    'transaction_category': 'salary',
                    'payment_method': 'NACH/ECS'
                }
            
            return transaction
            
        return None
    
    def _clean_merchant_name(self, raw_merchant: str) -> str:
        """Clean and extract meaningful merchant name"""
        # Remove common prefixes
        merchant = raw_merchant.replace('PAY*', '').strip()
        
        # Common merchant mappings
        merchant_mappings = {
            'Swiggy': 'Swiggy',
            'SWIGGY': 'Swiggy',
            'ZOMATO': 'Zomato',
            'AMAZON': 'Amazon',
            'FLIPKART': 'Flipkart',
            'UBER': 'Uber',
            'OLA': 'Ola'
        }
        
        for key, value in merchant_mappings.items():
            if key in merchant.upper():
                return value
                
        return merchant
    
    def _extract_employer_name(self, remitter_code: str) -> str:
        """Extract employer name from NACH remitter code"""
        if 'AMAZON' in remitter_code.upper():
            return 'Amazon Development Centre India'
        elif 'SAL' in remitter_code.upper():
            # Extract company name from salary code
            parts = remitter_code.split('-')
            for part in parts:
                if len(part) > 5 and 'SAL' not in part and 'CR' not in part:
                    return part.replace('AMAZONDEVELCENTI', 'Amazon Development Centre India')
        
    def parse_indusind_transaction(self, email_content: str) -> Optional[Dict]:
        """Parse IndusInd Bank transaction email content"""
        transaction = {}
        
        # Pattern for IndusInd credit card transaction
        indusind_match = re.search(r'transaction on your IndusInd Bank Credit Card ending (\d{4}) for INR ([\d,]+\.\d{2}) on (\d{2}-\d{2}-\d{4}) (\d{2}:\d{2}:\d{2}) \w+ at ([^\\s]+) is Approved', email_content, re.IGNORECASE)
        
        if indusind_match:
            # Extract merchant name from location/description
            raw_merchant = indusind_match.group(5).strip()
            merchant = self._clean_indusind_merchant(raw_merchant)
            
            transaction = {
                'amount': float(indusind_match.group(2).replace(',', '')),
                'merchant': merchant,
                'card_last4': indusind_match.group(1),
                'date': indusind_match.group(3),
                'time': indusind_match.group(4),
                'transaction_type': 'debit',
                'raw_merchant': raw_merchant
            }
            
            # Parse date to standard format (DD-MM-YYYY to YYYY-MM-DD)
            if transaction.get('date'):
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(transaction['date'], '%d-%m-%Y')
                    transaction['date'] = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
                    
            transaction['bank'] = 'IndusInd'
            
            # Add metadata
            transaction['metadata'] = {
                'source': 'email',
                'card_type': 'credit',
                'transaction_category': 'card'
            }
            
            return transaction
            
        return None
    
    def _clean_indusind_merchant(self, raw_merchant: str) -> str:
        """Clean IndusInd merchant name"""
        # Remove 'Upi ' prefix but keep the actual merchant name
        if raw_merchant.startswith('Upi '):
            return raw_merchant[4:].strip()  # Remove 'Upi ' prefix
        
        # Return as-is for now, we'll do mapping later
        return raw_merchant

    def get_bank_transactions(self, bank_email: str, bank_name: str, limit: int = 50) -> List[Dict]:
        """Get transactions from specific bank email"""
        if not self.service:
            self.authenticate()
            
        # Search for bank emails
        results = self.service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            q=f'from:{bank_email}',
            maxResults=limit
        ).execute()

        messages = results.get('messages', [])
        transactions = []
        seen_transactions = set()  # Track duplicates
        
        print(f"📬 Found {len(messages)} {bank_name} messages")
        
        for msg in messages:
            try:
                email_content = self.get_email_content(msg['id'])
                
                if bank_name.upper() == 'HSBC':
                    transaction = self.parse_hsbc_transaction(email_content)
                elif bank_name.upper() == 'KOTAK':
                    transaction = self.parse_kotak_transaction(email_content)                    
                elif bank_name.upper() == 'INDUSIND':
                    transaction = self.parse_indusind_transaction(email_content)
                    
                else:
                    # Add parsers for other banks here
                    transaction = None
                    
                if transaction:
                    transaction['metadata']['email_id'] = msg['id']
                    
                    # Create unique key for deduplication
                    unique_key = (
                        transaction.get('reference_number'),
                        transaction.get('amount'),
                        transaction.get('date'),
                        transaction.get('bank')
                    )
                    
                    # Only add if not seen before
                    if unique_key not in seen_transactions:
                        seen_transactions.add(unique_key)
                        
                        # Convert to structured model
                        structured_transaction = TransactionFactory.create_transaction(transaction)
                        transactions.append(transaction_to_dict(structured_transaction))
                    else:
                        print(f"  ⚠️ Skipping duplicate: ₹{transaction['amount']} on {transaction['date']}")
                    
            except Exception as e:
                print(f"❌ Error processing message {msg['id']}: {e}")
                continue
                
        return transactions

    def get_all_bank_transactions(self) -> Dict[str, List[Dict]]:
        """Get transactions from all supported banks"""
        bank_configs = {
            # 'HSBC': ['hsbc@mail.hsbc.co.in', 'alerts@mail.hsbc.co.in'],
            'Kotak': ['BankAlerts@kotak.com', 'bankalerts@kotak.com', 'nach.alerts@kotak.com'],
            'IndusInd': ['transactionalert@indusind.com'],
            # Add more banks here
            # 'SBI': ['sbi@sbi.co.in'],
            # 'ICICI': ['alerts@icicibank.com']
        }
        
        all_transactions = {}
        
        for bank_name, emails in bank_configs.items():
            print(f"\n--- {bank_name} Transactions ---")
            bank_transactions = []
            seen_transactions = set()  # Track duplicates across all emails for this bank
            
            for email in emails:
                print(f"📧 Checking {email}")
                transactions = self.get_bank_transactions_with_dedup(email, bank_name, seen_transactions)
                bank_transactions.extend(transactions)
                
            all_transactions[bank_name] = bank_transactions
            print(f"✅ Found {len(bank_transactions)} total {bank_name} transactions")
            
        return all_transactions
    
    def get_bank_transactions_with_dedup(self, bank_email: str, bank_name: str, seen_transactions: set, limit: int = 50) -> List[Dict]:
        """Get transactions from specific bank email with deduplication"""
        if not self.service:
            self.authenticate()
            
        # Search for bank emails
        results = self.service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            q=f'from:{bank_email}',
            maxResults=limit
        ).execute()

        messages = results.get('messages', [])
        transactions = []
        
        print(f"📬 Found {len(messages)} {bank_name} messages")
        
        for msg in messages:
            try:
                email_content = self.get_email_content(msg['id'])
                
                if bank_name.upper() == 'HSBC':
                    transaction = self.parse_hsbc_transaction(email_content)
                elif bank_name.upper() == 'KOTAK':
                    transaction = self.parse_kotak_transaction(email_content)                    
                elif bank_name.upper() == 'INDUSIND':
                    transaction = self.parse_indusind_transaction(email_content)
                    
                else:
                    # Add parsers for other banks here
                    transaction = None
                    
                if transaction:
                    transaction['metadata']['email_id'] = msg['id']
                    
                    # Create unique key for deduplication
                    unique_key = (
                        transaction.get('reference_number'),
                        transaction.get('amount'),
                        transaction.get('date'),
                        transaction.get('bank')
                    )
                    
                    # Only add if not seen before
                    if unique_key not in seen_transactions:
                        seen_transactions.add(unique_key)
                        
                        # Convert to structured model
                        structured_transaction = TransactionFactory.create_transaction(transaction)
                        transactions.append(transaction_to_dict(structured_transaction))
                    else:
                        print(f"  ⚠️ Skipping duplicate: ₹{transaction['amount']} on {transaction['date']}")
                    
            except Exception as e:
                print(f"❌ Error processing message {msg['id']}: {e}")
                continue
                
        return transactions

    def save_transactions_to_json(self, transactions: Dict[str, List[Dict]], filename: str = "email_transactions.json"):
        """Save transactions to JSON file"""
        with open(filename, 'w') as f:
            json.dump(transactions, f, indent=2, default=str)
        print(f"💾 Transactions saved to {filename}")

    def get_transaction_summary(self, transactions: Dict[str, List[Dict]]) -> Dict:
        """Generate summary of email transactions"""
        summary = {
            'total_transactions': 0,
            'total_credit_amount': 0,
            'total_credit_count': 0,
            'total_debit_amount': 0,
            'total_debit_count': 0,
            'net_change': 0,
            'banks': {},
            'date_range': {'earliest': None, 'latest': None}
        }
        
        all_dates = []
        
        for bank, bank_transactions in transactions.items():
            bank_credit_amount = 0
            bank_credit_count = 0
            bank_debit_amount = 0
            bank_debit_count = 0
            
            for t in bank_transactions:
                amount = t.get('amount', 0)
                tx_type = t.get('transaction_type', 'debit')
                
                if tx_type == 'credit':
                    bank_credit_amount += amount
                    bank_credit_count += 1
                    summary['total_credit_amount'] += amount
                    summary['total_credit_count'] += 1
                else:
                    bank_debit_amount += amount
                    bank_debit_count += 1
                    summary['total_debit_amount'] += amount
                    summary['total_debit_count'] += 1
                
                # Collect dates
                if t.get('date'):
                    all_dates.append(t['date'])
            
            summary['banks'][bank] = {
                'count': len(bank_transactions),
                'credit_amount': bank_credit_amount,
                'credit_count': bank_credit_count,
                'debit_amount': bank_debit_amount,
                'debit_count': bank_debit_count,
                'net_change': bank_credit_amount - bank_debit_amount
            }
            summary['total_transactions'] += len(bank_transactions)
        
        summary['net_change'] = summary['total_credit_amount'] - summary['total_debit_amount']
        
        if all_dates:
            summary['date_range']['earliest'] = min(all_dates)
            summary['date_range']['latest'] = max(all_dates)
            
        return summary

def main():
    reader = GmailTransactionReader()
    
    # Authenticate
    reader.authenticate()
    print("✅ Gmail Connected Successfully")
    
    # Get all transactions
    all_transactions = reader.get_all_bank_transactions()
    
    # Save to file
    reader.save_transactions_to_json(all_transactions)
    
    # Print summary
    summary = reader.get_transaction_summary(all_transactions)
    print(f"\n📊 Transaction Summary:")
    print(f"Total Transactions: {summary['total_transactions']}")
    print(f"Total Credits: ₹{summary['total_credit_amount']:,.2f} ({summary['total_credit_count']} transactions)")
    print(f"Total Debits: ₹{summary['total_debit_amount']:,.2f} ({summary['total_debit_count']} transactions)")
    print(f"Net Change: ₹{summary['net_change']:,.2f}")
    print(f"Date Range: {summary['date_range']['earliest']} to {summary['date_range']['latest']}")
    
    for bank, stats in summary['banks'].items():
        print(f"{bank}: {stats['count']} transactions, Net: ₹{stats['net_change']:,.2f}")
        print(f"  Credits: ₹{stats['credit_amount']:,.2f} ({stats['credit_count']})")
        print(f"  Debits: ₹{stats['debit_amount']:,.2f} ({stats['debit_count']})")

if __name__ == "__main__":
    main()
