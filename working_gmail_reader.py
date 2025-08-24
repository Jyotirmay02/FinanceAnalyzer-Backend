#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from credentials.enhanced_gmail_reader import GmailTransactionReader

def get_all_transactions():
    """Get all transactions from all banks - working version"""
    print("🚀 COMPREHENSIVE TRANSACTION EXTRACTION")
    print("=" * 50)
    
    # Working account only
    email_account = 'jotirmays123@gmail.com'
    
    # All bank configurations with correct email addresses
    bank_configs = {
        'ICICI_CC': ['credit_cards@icicibank.com'],
        'CANARA': ['canarabank@canarabank.com'],
        'SBI_CC': ['Offers@sbicard.com', 'emailer@sbicard.com'],
        'Kotak': ['BankAlerts@kotak.com'],
        'IndusInd': ['transactionalert@indusind.com']
    }
    
    try:
        reader = GmailTransactionReader(email_account)
        reader.authenticate()
        print(f"✅ {email_account} authenticated")
        
        all_transactions = {}
        
        for bank_name, email_addresses in bank_configs.items():
            print(f"\n🏦 Processing {bank_name}...")
            bank_transactions = []
            
            for email_addr in email_addresses:
                print(f"  📧 Searching {email_addr}...")
                
                try:
                    # Search for emails
                    results = reader.service.users().messages().list(
                        userId='me',
                        q=f'from:{email_addr}',
                        maxResults=10
                    ).execute()
                    
                    messages = results.get('messages', [])
                    print(f"    📨 Found {len(messages)} emails")
                    
                    for i, message in enumerate(messages):
                        try:
                            # Get email content
                            email_content = reader.get_email_content(message['id'])
                            
                            # Parse based on bank
                            transaction = None
                            if bank_name == 'ICICI_CC':
                                transaction = reader.parse_icici_credit_card_transaction(email_content)
                            elif bank_name == 'CANARA':
                                transaction = reader.parse_canara_bank_transaction(email_content)
                            elif bank_name == 'SBI_CC':
                                transaction = reader.parse_sbi_credit_card_transaction(email_content)
                            elif bank_name == 'Kotak':
                                transaction = reader.parse_kotak_transaction(email_content)
                            elif bank_name == 'IndusInd':
                                transaction = reader.parse_indusind_transaction(email_content)
                            
                            if transaction:
                                transaction['metadata'] = {
                                    'source': 'email',
                                    'email_id': message['id'],
                                    'email_address': email_addr
                                }
                                bank_transactions.append(transaction)
                                print(f"    ✅ Parsed: ₹{transaction.get('amount', 0)} - {transaction.get('merchant', 'N/A')[:30]}")
                            
                        except Exception as e:
                            print(f"    ⚠️ Error processing email {i+1}: {str(e)[:30]}...")
                            continue
                    
                except Exception as e:
                    print(f"    ❌ Error searching {email_addr}: {str(e)[:50]}...")
                    continue
            
            if bank_transactions:
                all_transactions[bank_name] = bank_transactions
                print(f"  ✅ {bank_name}: {len(bank_transactions)} transactions")
            else:
                print(f"  ❌ {bank_name}: No transactions found")
        
        # Save results
        if all_transactions:
            filename = 'comprehensive_transactions.json'
            with open(filename, 'w') as f:
                json.dump(all_transactions, f, indent=2, default=str)
            
            print(f"\n💾 Saved to: {filename}")
            
            # Print summary
            print(f"\n📊 SUMMARY:")
            total_transactions = 0
            total_amount = 0
            
            for bank, transactions in all_transactions.items():
                count = len(transactions)
                amount = sum(float(t.get('amount', 0)) for t in transactions)
                total_transactions += count
                total_amount += amount
                
                print(f"  🏦 {bank}: {count} transactions, ₹{amount:,.2f}")
            
            print(f"\n🎉 TOTAL: {total_transactions} transactions, ₹{total_amount:,.2f}")
        else:
            print(f"\n❌ No transactions found from any bank")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    get_all_transactions()
