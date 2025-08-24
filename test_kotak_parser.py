from credentials.enhanced_gmail_reader import GmailTransactionReader

def test_kotak_parsing():
    """Test Kotak email parsing with sample emails"""
    
    # Card transaction
    card_email = """
    Dear Customer,
    Your transaction of Rs.216.00 on PAY*Swiggy using Kotak Bank Debit Card XX6999 on 15/08/2025 21:37:28 from your account XX1321 has been processed.
    The transaction reference No is 522716024255 & Available balance is Rs.460910.00.
    """
    
    # IMPS Debit
    imps_debit_email = """
    Dear JYOTIRMAY SETHI,
    We wish to inform you that your account xx1321 is debited for Rs. 250000.00 on 17-Aug-2025 towards IMPS.
    Please find the details as below:
    Beneficiary Name: Mr. JYOTIRMAY SETHI
    Beneficiary Account No: XX1739
    Beneficiary IFSC: SBIN0006933
    IMPS Reference No: 522921331052
    Remarks: GOLD LOAN
    """
    
    # IMPS Credit
    imps_credit_email = """
    Dear JYOTIRMAY SETHI
    We wish to inform you that your account xx1321 is credited by Rs. 284198.00 on 01-Aug-2025 for IMPS transaction.
    Please find the details as below:
    Sender Name: AMAZON DEVELOPMENT CENTRE INDIA PRIVATE LIMITED
    Sender Mobile No: 9111XX1111
    IMPS Reference No: 521310627144
    Remarks : PDY003067438032
    """
    
    # NACH Credit
    nach_email = """
    Dear Customer,
    Your account XXXXXXXX1321 has been credited with payment received via NACH/ECS as per details below.
    Remitter : NACH-SAL-CR-SAL-AMAZONDEVELCENTI-SALARYAMAZONADCI
    Amount: Rs.65,400.00
    Transaction date : 30/07/2025
    """
    
    reader = GmailTransactionReader()
    
    print("🧪 Testing Kotak Email Parser")
    print("=" * 50)
    
    test_cases = [
        ("Card Transaction", card_email),
        ("IMPS Debit", imps_debit_email),
        ("IMPS Credit", imps_credit_email),
        ("NACH Credit", nach_email)
    ]
    
    for name, email in test_cases:
        print(f"\n📧 Testing {name}:")
        transaction = reader.parse_kotak_transaction(email)
        if transaction:
            print("✅ Successfully parsed:")
            for key, value in transaction.items():
                print(f"  {key}: {value}")
        else:
            print("❌ Failed to parse transaction")

if __name__ == "__main__":
    test_kotak_parsing()
