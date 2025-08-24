import json

def analyze_transactions():
    """Analyze transaction summary with proper credit/debit breakdown"""
    
    with open('email_transactions.json', 'r') as f:
        data = json.load(f)
    
    total_credit_amount = 0
    total_credit_count = 0
    total_debit_amount = 0
    total_debit_count = 0
    
    bank_summary = {}
    
    for bank, transactions in data.items():
        bank_credit_amount = 0
        bank_credit_count = 0
        bank_debit_amount = 0
        bank_debit_count = 0
        
        for transaction in transactions:
            amount = transaction['amount']
            tx_type = transaction['transaction_type']
            
            if tx_type == 'credit':
                total_credit_amount += amount
                total_credit_count += 1
                bank_credit_amount += amount
                bank_credit_count += 1
            elif tx_type == 'debit':
                total_debit_amount += amount
                total_debit_count += 1
                bank_debit_amount += amount
                bank_debit_count += 1
        
        bank_summary[bank] = {
            'credit_amount': bank_credit_amount,
            'credit_count': bank_credit_count,
            'debit_amount': bank_debit_amount,
            'debit_count': bank_debit_count,
            'net_change': bank_credit_amount - bank_debit_amount,
            'total_transactions': bank_credit_count + bank_debit_count
        }
    
    net_change = total_credit_amount - total_debit_amount
    total_transactions = total_credit_count + total_debit_count
    
    print("📊 EMAIL TRANSACTION ANALYSIS")
    print("=" * 50)
    
    print(f"\n💰 OVERALL SUMMARY:")
    print(f"Total Transactions: {total_transactions}")
    print(f"Total Credit Amount: ₹{total_credit_amount:,.2f} ({total_credit_count} transactions)")
    print(f"Total Debit Amount: ₹{total_debit_amount:,.2f} ({total_debit_count} transactions)")
    print(f"Net Change: ₹{net_change:,.2f}")
    
    print(f"\n🏦 BANK-WISE BREAKDOWN:")
    for bank, summary in bank_summary.items():
        print(f"\n{bank}:")
        print(f"  Credits: ₹{summary['credit_amount']:,.2f} ({summary['credit_count']} transactions)")
        print(f"  Debits: ₹{summary['debit_amount']:,.2f} ({summary['debit_count']} transactions)")
        print(f"  Net Change: ₹{summary['net_change']:,.2f}")
        print(f"  Total Transactions: {summary['total_transactions']}")
    
    # Transaction category breakdown for Kotak
    if 'Kotak' in data:
        print(f"\n📋 KOTAK TRANSACTION CATEGORIES:")
        categories = {}
        for transaction in data['Kotak']:
            category = transaction.get('metadata', {}).get('transaction_category', 'unknown')
            if category not in categories:
                categories[category] = {'count': 0, 'amount': 0}
            categories[category]['count'] += 1
            categories[category]['amount'] += transaction['amount']
        
        for category, stats in categories.items():
            print(f"  {category.title()}: {stats['count']} transactions, ₹{stats['amount']:,.2f}")

if __name__ == "__main__":
    analyze_transactions()
