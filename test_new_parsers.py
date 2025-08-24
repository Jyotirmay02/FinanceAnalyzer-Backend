#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from credentials.enhanced_gmail_reader import GmailTransactionReader

def test_new_parsers():
    """Test the new bank parsers with sample data"""
    reader = GmailTransactionReader('test@example.com')
    
    print("🧪 Testing New Bank Parsers")
    print("=" * 40)
    
    # Test ICICI Credit Card
    icici_email = """
    ICICI Bank Online Dear Customer, Your ICICI Bank Credit Card XX6007 has been used for a transaction of INR 114.00 on Aug 24, 2025 at 10:26:07. Info: TPNODL. The Available Credit Limit on your card is INR 1,50,169.96 and Total Credit Limit is INR 1,50,000.00.
    """
    
    print("\n💳 Testing ICICI Credit Card:")
    icici_result = reader.parse_icici_credit_card_transaction(icici_email)
    if icici_result:
        print("✅ Successfully parsed:")
        print(f"  Card: {icici_result['account_number']}")
        print(f"  Amount: ₹{icici_result['amount']}")
        print(f"  Date: {icici_result['date']}")
        print(f"  Merchant: {icici_result['merchant']}")
    else:
        print("❌ Failed to parse")
    
    # Test Canara Bank
    canara_email = """
    Dear Customer,
    
    Thanking you for banking with Canara Bank.
    
    An amount of INR 25.00 has been DEBITED to your account XXXX5159 on 24/08/2025. Total Avail.bal INR 79,770.73.To report fraud & stop further debit SMS SUSPECT to 56161.
    """
    
    print("\n🏦 Testing Canara Bank:")
    canara_result = reader.parse_canara_bank_transaction(canara_email)
    if canara_result:
        print("✅ Successfully parsed:")
        print(f"  Account: {canara_result['account_number']}")
        print(f"  Amount: ₹{canara_result['amount']}")
        print(f"  Type: {canara_result['transaction_type']}")
        print(f"  Date: {canara_result['date']}")
        print(f"  Balance: ₹{canara_result['balance']}")
    else:
        print("❌ Failed to parse")
    
    # Test SBI Credit Card
    sbi_cc_email = """
    Your SimplyCLICK SBI Card Monthly Statement -Aug 2025
    """
    
    print("\n💳 Testing SBI Credit Card:")
    sbi_cc_result = reader.parse_sbi_credit_card_transaction(sbi_cc_email)
    if sbi_cc_result:
        print("✅ Successfully parsed:")
        print(f"  Type: {sbi_cc_result['transaction_type']}")
        print(f"  Merchant: {sbi_cc_result['merchant']}")
    else:
        print("❌ Failed to parse")

if __name__ == "__main__":
    test_new_parsers()
