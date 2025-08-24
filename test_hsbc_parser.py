from credentials.enhanced_gmail_reader import GmailTransactionReader

def test_hsbc_parsing():
    """Test HSBC email parsing with sample email"""
    
    sample_email = """
    Dear Customer,

    We write to confirm that your Credit card no ending with 1032,has been used for INR 223.00 for payment to SWIGGY LIMITED on 23 Aug 2025 at 22:08.

    If you want to report this as a fraud transaction and block your card,
    For Retail cards:
    Please call 18002673456 (from India)or +914061268002 (from overseas)
    Or SMS 'BLOCK HSBC CC last 4 digits of your card number to '575750' from your registered mobile number.

    For corporate cards,
    Please call 18001216922 (from India)or +914071898009 (from overseas). or place a block card request on https://mivision.hsbc.co.in

    For any other details please,
    Call PhoneBanking* or
    Through HSBC Internet Banking (if you have registered for it)
    (This is a system generated communication and hence please do not reply to this email)

    HSBC Bank
    """
    
    reader = GmailTransactionReader()
    transaction = reader.parse_hsbc_transaction(sample_email)
    
    print("🧪 Testing HSBC Email Parser")
    print("=" * 50)
    
    if transaction:
        print("✅ Successfully parsed transaction:")
        for key, value in transaction.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Failed to parse transaction")
        
        # Debug: Test individual patterns
        import re
        patterns = {
            'card_last4': r'ending with (\d{4})',
            'amount': r'INR\s*([\d,]+\.\d{2})',
            'merchant': r'payment to ([A-Z0-9 &\-\.]+?) on',
            'date': r'on (\d{1,2} \w+ \d{4}) at',
            'time': r'at (\d{2}:\d{2})'
        }
        
        print("\n🔍 Debug - Pattern Matches:")
        for key, pattern in patterns.items():
            match = re.search(pattern, sample_email, re.IGNORECASE)
            if match:
                print(f"  ✅ {key}: {match.group(1)}")
            else:
                print(f"  ❌ {key}: No match")

if __name__ == "__main__":
    test_hsbc_parsing()
