from credentials.enhanced_gmail_reader import GmailTransactionReader

def test_hsbc_credit_parsing():
    """Test HSBC credit email parsing"""
    
    credit_email = """
    Dear Customer,
    We have received credits of ₹ 122.00 on your HSBC credit card ending with 1032 on 19/08/2025. The amount has been adjusted against your outstanding balance. Kindly make the remaining payment of ₹ 2,271.63 within timeline to avoid any finance charges.
    Yours sincerely,
    HSBC India.
    """
    
    debit_email = """
    Dear Customer,
    We write to confirm that your Credit card no ending with 1032,has been used for INR 223.00 for payment to SWIGGY LIMITED on 23 Aug 2025 at 22:08.
    """
    
    reader = GmailTransactionReader()
    
    print("🧪 Testing HSBC Credit Email Parser")
    print("=" * 50)
    
    # Test credit transaction
    print("\n📈 Testing Credit Transaction:")
    credit_transaction = reader.parse_hsbc_transaction(credit_email)
    if credit_transaction:
        print("✅ Successfully parsed credit:")
        for key, value in credit_transaction.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Failed to parse credit transaction")
    
    # Test debit transaction
    print("\n📉 Testing Debit Transaction:")
    debit_transaction = reader.parse_hsbc_transaction(debit_email)
    if debit_transaction:
        print("✅ Successfully parsed debit:")
        for key, value in debit_transaction.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Failed to parse debit transaction")

if __name__ == "__main__":
    test_hsbc_credit_parsing()
