"""
Constants and configuration for transaction categorization
"""

from enum import Enum
from typing import Dict

class ColumnKey(Enum):
    """Column names for bank statement data"""
    TXN_DATE = "Txn Date"
    VALUE_DATE = "Value Date"
    CHEQUE_NO = "Cheque No."
    DESCRIPTION = "Description"
    BRANCH_CODE = "Branch Code"
    DEBIT = "Debit"
    CREDIT = "Credit"
    BALANCE = "Balance"

# Column index mapping
COLUMN_INDEX: Dict[ColumnKey, int] = {
    ColumnKey.TXN_DATE: 0,
    ColumnKey.VALUE_DATE: 1,
    ColumnKey.CHEQUE_NO: 2,
    ColumnKey.DESCRIPTION: 3,
    ColumnKey.BRANCH_CODE: 4,
    ColumnKey.DEBIT: 5,
    ColumnKey.CREDIT: 6,
    ColumnKey.BALANCE: 7
}

# Category keywords for transaction classification
CATEGORY_KEYWORDS: Dict[str, str] = {
    # SBI-specific mappings
    "CREDIT INTEREST": "Interest",
    "INTEREST": "Interest", 
    "HSBC0560002": "Amazon - Reimbursement",
    "11157594174": "Dad",
    "159CNR": "Self-Canara",
    "36515075873": "Credit Card Payment",
    "NITK SURATHKAL": "Refund",
    "41860880772": "Mommy",
    "HOMELOAN": "Processing Fee",
    "HOME LOAN": "Processing Fee",
    "Salary": "Salary",
    "SAL": "Salary",
    "42560298142": "Loan Account 1",
    "CASH WITHDRAWAL SELF": "Cheq",
    "Cheq": "Cheq",
    "CRED": "Credit Card Payment",
    "30220265996": "Adaitya",
    "Stamp duty": "Processing Fee",
    "20227196892": "Notary",
    "TATA STEEL AASHIYANA": "Gangadhar Hardware",
    "30341164912": "Gangadhar Hardware",
    "806FDRL": "Mantu-Plot",
    "CNRB-xx159": "Self Canara",
    "KKBK-xx321": "Self Kotak",
    "ISKCON": "Donation",
    "PUNB-xx686": "Cement",
    "872HDFC": "Home Plan",
    "PUNB-xx362": "Bhagabat",
    "43772632759": "Loan Account 2",
    "ZEPTO": "Shopping",
    "CNB-XX159": "Self Canara",
    "JYOTIRMA": "Self Canara",
    "Gangadhar Hardware": "Gangadhar Hardware",
    "IOBA-xx196": "Rabindra",
    "Rabindra": "Rabindra",
    "SRIJAGANNAT": "Donation",
    "RECOVERIES FOR TPE-ADVOCATE": "Processing Fee",

    # Smart Self Transfers (order matters - more specific first)
    "sbin/**1739": "Self Transfer - SBI",
    "jyotirmay/The state": "Self Transfer - SBI",
    "jyotirmay/SBIN": "Self Transfer - SBI",
    "jyotirmay/CNRB": "Self Transfer - Canara",
    "jyotirmay/KMB": "Self Transfer - Kotak",
    "@amazonpay": "Self Transfer - Amazon Pay",
    "jyotirmay": "Self Transfer",
    "41083981739": "Self Transfer - SBI",  # Jyotirmay's SBI account number
    
    # Food & Dining
    "swiggy": "Food & Dining",
    "zomato": "Food & Dining",
    "dominos": "Food & Dining",
    "mcdonald": "Food & Dining",
    
    # Shopping
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "myntra": "Shopping",
    "rituraj": "Shopping",
    
    # Travel
    "ola": "Travel",
    "uber": "Travel",
    "redbus": "Travel",
    "irctc": "Travel",
    
    # Mobile & Recharge
    "airtel": "Mobile Recharge", # Exception - UPI/DR/552512635971/Iskcon Ba/AIRP/**24pos@mairtel/Paid via//YCD01JX7BTCX8HRGWPJS4X02SF1JTPzW6Lg/08/06/2025 14:21:56
    "jio": "Mobile Recharge",
    "vi ": "Mobile Recharge",
    "recharge": "Mobile Recharge",
    
    # Investment
    "zerodha": "Investment",
    "groww": "Investment",
    "mutual": "Investment",
    "indianclearingcorp": "Investment",
    
    # Banking & Transfers
    "upi": "UPI Transfer",
    "apy": "APY",
    "atm": "ATM Withdrawal",
    "sbint": "Interest",
    
    # Bank Charges & Fees
    "debit card annual charges": "Bank Charges",
    "sms": "Bank Charges",
    
    # Insurance & Schemes
    "pmsby": "PMSBY",
    
    # UNI PAY
    "northern": "UNI PAY",
    
    # Other categories
    "refund": "Refunds",
    "AMAZONDEVEL": "SALARY",
}

# Configuration
DEFAULT_DATA_START_ROW = 26  # Row where transaction data begins (0-indexed) - for Excel
CSV_DATA_START_ROW = 0       # Row where headers are located for simple CSV files
BANK_STATEMENT_CSV_DATA_START_ROW = 0  # Row where headers are located for bank statement CSV files (after processing)
DEFAULT_SHEET_NAME = "1754113304898"  # Default sheet name to process (Excel only)
