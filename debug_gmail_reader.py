#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from credentials.enhanced_gmail_reader import GmailTransactionReader, EMAIL_ACCOUNTS

def debug_bank_search():
    """Debug version with timeout and limited emails"""
    print("🔍 DEBUG: Testing Bank Email Search")
    print("=" * 40)
    
    # Test banks to search
    test_banks = {
        'ICICI_CC': ['credit_cards@icicibank.com'],
        'SBI_CC': ['sbicard.com'],
        'CANARA': ['canarabank@canarabank.com'],
        'HSBC': ['mail@hsbc.co.in'],
        'Kotak': ['BankAlerts@kotak.com'],
        'IndusInd': ['transactionalert@indusind.com']
    }
    
    for email_account in EMAIL_ACCOUNTS:
        print(f"\n📧 Testing {email_account}...")
        
        try:
            reader = GmailTransactionReader(email_account)
            reader.authenticate()
            print("✅ Authentication successful")
            
            found_banks = {}
            
            for bank_name, emails in test_banks.items():
                print(f"\n🏦 Testing {bank_name}:")
                
                bank_transactions = []
                
                for email_addr in emails:
                    try:
                        print(f"  🔍 Searching {email_addr}...")
                        
                        # Search with limit 5 for debugging
                        results = reader.service.users().messages().list(
                            userId='me',
                            q=f'from:{email_addr}',
                            maxResults=5
                        ).execute()
                        
                        messages = results.get('messages', [])
                        print(f"    📨 Found {len(messages)} emails")
                        
                        if messages:
                            # Test parsing first email
                            msg = reader.service.users().messages().get(
                                userId='me', id=messages[0]['id'], format='metadata'
                            ).execute()
                            
                            headers = msg['payload'].get('headers', [])
                            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                            
                            print(f"    📧 Sample: {sender}")
                            print(f"    📝 Subject: {subject[:50]}...")
                            
                            # Try parsing
                            email_content = reader.get_email_content(messages[0]['id'])
                            
                            transaction = None
                            if bank_name == 'ICICI_CC':
                                transaction = reader.parse_icici_credit_card_transaction(email_content)
                            elif bank_name == 'SBI_CC':
                                transaction = reader.parse_sbi_credit_card_transaction(email_content)
                            elif bank_name == 'CANARA':
                                transaction = reader.parse_canara_bank_transaction(email_content)
                            elif bank_name == 'HSBC':
                                transaction = reader.parse_hsbc_transaction(email_content)
                            elif bank_name == 'Kotak':
                                transaction = reader.parse_kotak_transaction(email_content)
                            elif bank_name == 'IndusInd':
                                transaction = reader.parse_indusind_transaction(email_content)
                            
                            if transaction:
                                print(f"    ✅ PARSED: ₹{transaction.get('amount', 0)} - {transaction.get('merchant', 'N/A')}")
                                bank_transactions.append(transaction)
                            else:
                                print(f"    ❌ Failed to parse")
                                print(f"    📄 Content preview: {email_content[:100]}...")
                        
                    except Exception as e:
                        print(f"    ❌ Error: {str(e)[:50]}...")
                        continue
                
                if bank_transactions:
                    found_banks[bank_name] = len(bank_transactions)
                    print(f"  ✅ {bank_name}: {len(bank_transactions)} transactions")
                else:
                    print(f"  ❌ {bank_name}: No transactions found")
            
            print(f"\n📊 {email_account} Summary:")
            for bank, count in found_banks.items():
                print(f"  • {bank}: {count} transactions")
                
        except Exception as e:
            print(f"❌ Error with {email_account}: {str(e)[:50]}...")
            continue

if __name__ == "__main__":
    debug_bank_search()
