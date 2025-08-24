#!/usr/bin/env python3

import json
import re
from collections import defaultdict, Counter

def analyze_existing_transactions():
    """Analyze existing transaction data to find patterns"""
    print("🔍 Analyzing existing transaction data...")
    
    try:
        with open('email_transactions_multi_account.json', 'r') as f:
            data = json.load(f)
        print("✅ Loaded existing transaction data")
    except FileNotFoundError:
        print("❌ No existing transaction data found")
        return
    
    print(f"📊 Found data for {len(data)} banks/institutions")
    
    # Analyze each bank's data
    for bank, transactions in data.items():
        print(f"\n🏦 {bank.upper()}:")
        print(f"  📈 {len(transactions)} transactions")
        
        if transactions:
            # Analyze transaction patterns
            transaction_types = Counter()
            merchants = Counter()
            methods = Counter()
            
            for txn in transactions:
                transaction_types[txn.get('transaction_type', 'unknown')] += 1
                merchants[txn.get('merchant', 'unknown')] += 1
                methods[txn.get('transaction_method', 'unknown')] += 1
            
            print(f"  💳 Transaction types: {dict(transaction_types)}")
            print(f"  🏪 Top merchants: {dict(merchants.most_common(3))}")
            print(f"  🔄 Methods: {dict(methods)}")
            
            # Sample transaction
            sample = transactions[0]
            print(f"  📝 Sample transaction:")
            for key, value in sample.items():
                if key != 'raw_content':
                    print(f"    {key}: {value}")

def find_missing_patterns():
    """Identify what patterns might be missing"""
    print("\n🔍 IDENTIFYING MISSING FINANCIAL INSTITUTIONS:")
    print("=" * 50)
    
    # Common Indian financial institutions
    common_banks = [
        'HDFC Bank', 'ICICI Bank', 'SBI', 'Axis Bank', 'Kotak Bank', 
        'IndusInd Bank', 'PNB', 'Canara Bank', 'Union Bank', 'BOB'
    ]
    
    common_cards = [
        'HDFC Credit Card', 'ICICI Credit Card', 'SBI Card', 'Axis Bank Card',
        'Kotak Credit Card', 'IndusInd Credit Card', 'American Express', 'Citibank'
    ]
    
    common_wallets = [
        'Paytm', 'PhonePe', 'Google Pay', 'Amazon Pay', 'Mobikwik', 'Freecharge'
    ]
    
    common_ecommerce = [
        'Amazon', 'Flipkart', 'Myntra', 'Zomato', 'Swiggy', 'Uber', 'Ola'
    ]
    
    # Check what we have vs what's common
    try:
        with open('email_transactions_multi_account.json', 'r') as f:
            existing_data = json.load(f)
        existing_banks = list(existing_data.keys())
    except:
        existing_banks = []
    
    print(f"✅ Currently parsing: {existing_banks}")
    
    print(f"\n🏦 COMMON BANKS (check if you have accounts):")
    for bank in common_banks:
        status = "✅" if any(bank.upper() in existing.upper() for existing in existing_banks) else "❓"
        print(f"  {status} {bank}")
    
    print(f"\n💳 COMMON CREDIT CARDS:")
    for card in common_cards:
        status = "✅" if any(card.split()[0].upper() in existing.upper() for existing in existing_banks) else "❓"
        print(f"  {status} {card}")
    
    print(f"\n📱 COMMON WALLETS:")
    for wallet in common_wallets:
        print(f"  ❓ {wallet}")
    
    print(f"\n🛒 COMMON E-COMMERCE:")
    for ecom in common_ecommerce:
        print(f"  ❓ {ecom}")

def suggest_next_steps():
    """Suggest what to implement next"""
    print(f"\n🎯 SUGGESTED NEXT STEPS:")
    print("=" * 30)
    
    print("1. 🏦 PRIORITY BANKS TO ADD:")
    print("   • HDFC Bank (very common)")
    print("   • ICICI Bank (very common)")
    print("   • Axis Bank (common)")
    
    print("\n2. 💳 CREDIT CARDS TO ADD:")
    print("   • HDFC Credit Card")
    print("   • ICICI Credit Card") 
    print("   • SBI Credit Card")
    
    print("\n3. 📱 WALLETS TO ADD:")
    print("   • Paytm")
    print("   • PhonePe")
    print("   • Google Pay")
    
    print("\n4. 🛒 E-COMMERCE TO ADD:")
    print("   • Amazon (purchase notifications)")
    print("   • Flipkart")
    print("   • Zomato/Swiggy")
    
    print("\n💡 RECOMMENDATION:")
    print("Focus on banks first (highest transaction volume)")
    print("Then credit cards (monthly statements)")
    print("Then wallets (frequent small transactions)")

def main():
    print("🚀 ANALYZING EXISTING FINANCIAL DATA")
    print("=" * 40)
    
    # Analyze what we have
    analyze_existing_transactions()
    
    # Find what's missing
    find_missing_patterns()
    
    # Suggest next steps
    suggest_next_steps()
    
    print(f"\n✅ ANALYSIS COMPLETE!")
    print("Ready to add more financial institution parsers!")

if __name__ == "__main__":
    main()
