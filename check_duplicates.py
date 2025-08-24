import json
from collections import defaultdict

def check_duplicates():
    """Check for duplicate transactions"""
    
    with open('email_transactions.json', 'r') as f:
        data = json.load(f)
    
    print("🔍 CHECKING FOR DUPLICATE TRANSACTIONS")
    print("=" * 50)
    
    for bank, transactions in data.items():
        print(f"\n🏦 {bank} Bank:")
        
        # Group by reference number
        ref_groups = defaultdict(list)
        email_groups = defaultdict(list)
        
        for i, transaction in enumerate(transactions):
            ref_num = transaction.get('reference_number')
            email_id = transaction.get('metadata', {}).get('email_id')
            
            if ref_num:
                ref_groups[ref_num].append((i, transaction))
            if email_id:
                email_groups[email_id].append((i, transaction))
        
        # Check reference number duplicates
        ref_duplicates = {k: v for k, v in ref_groups.items() if len(v) > 1}
        if ref_duplicates:
            print(f"  📋 Reference Number Duplicates: {len(ref_duplicates)}")
            for ref_num, txns in ref_duplicates.items():
                print(f"    Ref {ref_num}: {len(txns)} transactions")
                for idx, txn in txns:
                    print(f"      - ₹{txn['amount']} on {txn['date']} (index {idx})")
        
        # Check email ID duplicates
        email_duplicates = {k: v for k, v in email_groups.items() if len(v) > 1}
        if email_duplicates:
            print(f"  📧 Email ID Duplicates: {len(email_duplicates)}")
            for email_id, txns in email_duplicates.items():
                print(f"    Email {email_id}: {len(txns)} transactions")
        
        if not ref_duplicates and not email_duplicates:
            print("  ✅ No duplicates found")

def deduplicate_transactions():
    """Remove duplicate transactions"""
    
    with open('email_transactions.json', 'r') as f:
        data = json.load(f)
    
    print("\n🧹 REMOVING DUPLICATES")
    print("=" * 30)
    
    for bank, transactions in data.items():
        original_count = len(transactions)
        
        # Deduplicate by reference number + amount + date
        seen = set()
        unique_transactions = []
        
        for transaction in transactions:
            # Create unique key
            key = (
                transaction.get('reference_number'),
                transaction.get('amount'),
                transaction.get('date'),
                transaction.get('metadata', {}).get('email_id')
            )
            
            if key not in seen:
                seen.add(key)
                unique_transactions.append(transaction)
        
        data[bank] = unique_transactions
        removed_count = original_count - len(unique_transactions)
        
        print(f"{bank}: {original_count} → {len(unique_transactions)} ({removed_count} duplicates removed)")
    
    # Save deduplicated data
    with open('email_transactions_deduplicated.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n💾 Deduplicated data saved to email_transactions_deduplicated.json")
    
    return data

if __name__ == "__main__":
    check_duplicates()
    deduplicate_transactions()
