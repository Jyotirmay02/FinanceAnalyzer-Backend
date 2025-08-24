from credentials.enhanced_gmail_reader import GmailTransactionReader

def test_indusind_parsing():
    """Test IndusInd email parsing"""
    
    # Test case 1: UPI with merchant code
    indusind_email1 = """
    IndusInd Bank

    The transaction on your IndusInd Bank Credit Card ending 1289 for INR 60.00 on 24-08-2025 09:33:22 am at Upi M226qki6pji2v is Approved. Available Limit: INR 210,763.93.
    """
    
    # Test case 2: UPI with actual merchant name
    indusind_email2 = """
    IndusInd Bank

    The transaction on your IndusInd Bank Credit Card ending 1289 for INR 200.00 on 23-08-2025 05:20:11 pm at Upi Gangadhar Hardware is Approved. Available Limit: INR 210,823.93.
    """
    
    reader = GmailTransactionReader()
    
    print("🧪 Testing IndusInd Email Parser")
    print("=" * 50)
    
    test_cases = [
        ("UPI with Code", indusind_email1),
        ("UPI with Merchant Name", indusind_email2)
    ]
    
    for name, email in test_cases:
        print(f"\n📧 Testing {name}:")
        transaction = reader.parse_indusind_transaction(email)
        if transaction:
            print("✅ Successfully parsed:")
            print(f"  Merchant: {transaction['merchant']}")
            print(f"  Raw Merchant: {transaction['raw_merchant']}")
            print(f"  Amount: ₹{transaction['amount']}")
            print(f"  Date: {transaction['date']}")
        else:
            print("❌ Failed to parse transaction")

if __name__ == "__main__":
    test_indusind_parsing()
