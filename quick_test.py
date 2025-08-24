#!/usr/bin/env python3

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from credentials.enhanced_gmail_reader import GmailTransactionReader

def quick_test():
    """Quick test of working account only"""
    print("🚀 QUICK TEST - Working Account Only")
    print("=" * 40)
    
    # Test only the working account
    email_account = 'jotirmays123@gmail.com'
    
    try:
        reader = GmailTransactionReader(email_account)
        reader.authenticate()
        print(f"✅ {email_account} authenticated")
        
        # Test the new banks
        test_results = {}
        
        # ICICI Credit Card
        print(f"\n💳 Testing ICICI Credit Card...")
        icici_transactions = reader.get_bank_transactions('credit_cards@icicibank.com', 'ICICI_CC', 5)
        test_results['ICICI_CC'] = len(icici_transactions)
        print(f"   Found: {len(icici_transactions)} transactions")
        
        # Canara Bank
        print(f"\n🏦 Testing Canara Bank...")
        canara_transactions = reader.get_bank_transactions('canarabank@canarabank.com', 'CANARA', 5)
        test_results['CANARA'] = len(canara_transactions)
        print(f"   Found: {len(canara_transactions)} transactions")
        
        # SBI Credit Card (try different email)
        print(f"\n💳 Testing SBI Credit Card...")
        sbi_cc_transactions = reader.get_bank_transactions('Offers@sbicard.com', 'SBI_CC', 5)
        test_results['SBI_CC'] = len(sbi_cc_transactions)
        print(f"   Found: {len(sbi_cc_transactions)} transactions")
        
        # Combine all transactions
        all_transactions = {
            'ICICI_CC': icici_transactions,
            'CANARA': canara_transactions,
            'SBI_CC': sbi_cc_transactions
        }
        
        # Save results
        with open('quick_test_results.json', 'w') as f:
            json.dump(all_transactions, f, indent=2, default=str)
        
        print(f"\n📊 RESULTS:")
        total = 0
        for bank, count in test_results.items():
            if count > 0:
                print(f"  ✅ {bank}: {count} transactions")
                total += count
            else:
                print(f"  ❌ {bank}: No transactions")
        
        print(f"\n🎉 Total: {total} new transactions found!")
        print(f"💾 Saved to: quick_test_results.json")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    quick_test()
