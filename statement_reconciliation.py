#!/usr/bin/env python3
"""
Statement Reconciliation Helper
Matches PDF statement transactions with email transactions for financial reconciliation
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re

@dataclass
class MatchResult:
    pdf_transaction: Dict
    email_transaction: Dict
    match_score: float
    match_type: str  # exact, fuzzy, partial

class StatementReconciler:
    def __init__(self):
        self.tolerance_amount = 1.0  # Amount tolerance for matching
        self.tolerance_days = 3      # Date tolerance in days
        
    def load_pdf_statements(self, statements_dir: str) -> Dict[str, List[Dict]]:
        """Load all PDF statement data"""
        pdf_data = {}
        
        for filename in os.listdir(statements_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(statements_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                # Extract bank and account type from filename
                parts = filename.replace('statement_data_', '').replace('_202508.json', '').split('_')
                if len(parts) >= 2:
                    bank = parts[0]
                    account_type = parts[1]
                    key = f"{bank}_{account_type}"
                    pdf_data[key] = data
                    
        return pdf_data
    
    def load_email_transactions(self, email_file: str) -> Dict[str, List[Dict]]:
        """Load email transaction data"""
        with open(email_file, 'r') as f:
            return json.load(f)
    
    def normalize_date(self, date_str: str) -> datetime:
        """Normalize date string to datetime object"""
        if not date_str:
            return None
            
        # Handle various date formats
        formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        return None
    
    def normalize_amount(self, amount) -> float:
        """Normalize amount to float"""
        if isinstance(amount, (int, float)):
            return float(amount)
        if isinstance(amount, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[₹$,\s]', '', amount)
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        return 0.0
    
    def calculate_match_score(self, pdf_txn: Dict, email_txn: Dict) -> Tuple[float, str]:
        """Calculate match score between PDF and email transactions"""
        score = 0.0
        match_type = "no_match"
        
        # Amount matching (40% weight)
        pdf_amount = self.normalize_amount(pdf_txn.get('amount', 0))
        email_amount = self.normalize_amount(email_txn.get('amount', 0))
        
        if abs(pdf_amount - email_amount) <= self.tolerance_amount:
            score += 40
            if abs(pdf_amount - email_amount) < 0.01:
                score += 10  # Bonus for exact amount match
        
        # Date matching (30% weight)
        pdf_date = self.normalize_date(pdf_txn.get('date', ''))
        email_date = self.normalize_date(email_txn.get('date', ''))
        
        if pdf_date and email_date:
            date_diff = abs((pdf_date - email_date).days)
            if date_diff <= self.tolerance_days:
                score += 30 - (date_diff * 5)  # Reduce score for each day difference
        
        # Description/Merchant matching (20% weight)
        pdf_desc = pdf_txn.get('description', '').lower()
        email_merchant = email_txn.get('merchant', '').lower()
        
        if email_merchant and email_merchant in pdf_desc:
            score += 20
        elif self.fuzzy_description_match(pdf_desc, email_merchant):
            score += 10
        
        # Transaction type matching (10% weight)
        pdf_type = pdf_txn.get('type', '').lower()
        email_type = email_txn.get('transaction_type', '').lower()
        
        if pdf_type == email_type:
            score += 10
        
        # Determine match type
        if score >= 80:
            match_type = "exact"
        elif score >= 60:
            match_type = "fuzzy"
        elif score >= 40:
            match_type = "partial"
        
        return score, match_type
    
    def fuzzy_description_match(self, pdf_desc: str, email_merchant: str) -> bool:
        """Fuzzy matching for descriptions"""
        if not pdf_desc or not email_merchant:
            return False
            
        # Common merchant name variations
        merchant_variations = {
            'zomato': ['zomato', 'zomato limited'],
            'swiggy': ['swiggy', 'www swiggy com'],
            'amazon': ['amazon', 'amazon pay', 'amzn'],
            'flipkart': ['flipkart', 'fkrt'],
            'paytm': ['paytm', 'paytm payments'],
            'uber': ['uber', 'uber india'],
            'ola': ['ola', 'ola cabs']
        }
        
        for key, variations in merchant_variations.items():
            if any(var in email_merchant for var in variations) and any(var in pdf_desc for var in variations):
                return True
        
        # Check if any word from merchant appears in description
        merchant_words = email_merchant.split()
        for word in merchant_words:
            if len(word) > 3 and word in pdf_desc:
                return True
        
        return False
    
    def reconcile_statements(self, pdf_data: Dict, email_data: Dict) -> Dict[str, List[MatchResult]]:
        """Reconcile PDF statements with email transactions"""
        results = {}
        
        for pdf_key, pdf_statements in pdf_data.items():
            print(f"\nReconciling {pdf_key}...")
            
            # Extract bank name for matching with email data
            bank_name = pdf_key.split('_')[0].lower()
            
            # Find corresponding email transactions
            email_txns = []
            for email_bank, txns in email_data.items():
                if bank_name in email_bank.lower() or email_bank.lower() in bank_name:
                    email_txns.extend(txns)
            
            if not email_txns:
                print(f"No email transactions found for {pdf_key}")
                continue
            
            matches = []
            
            # Process each PDF statement
            for statement in pdf_statements:
                pdf_txns = statement.get('transactions', [])
                
                for pdf_txn in pdf_txns:
                    best_match = None
                    best_score = 0
                    
                    for email_txn in email_txns:
                        score, match_type = self.calculate_match_score(pdf_txn, email_txn)
                        
                        if score > best_score and score >= 40:  # Minimum threshold
                            best_score = score
                            best_match = MatchResult(
                                pdf_transaction=pdf_txn,
                                email_transaction=email_txn,
                                match_score=score,
                                match_type=match_type
                            )
                    
                    if best_match:
                        matches.append(best_match)
            
            results[pdf_key] = matches
            print(f"Found {len(matches)} matches for {pdf_key}")
        
        return results
    
    def generate_reconciliation_report(self, matches: Dict[str, List[MatchResult]], output_file: str):
        """Generate reconciliation report"""
        report = {
            "reconciliation_summary": {},
            "matches": {},
            "generated_at": datetime.now().isoformat()
        }
        
        total_matches = 0
        total_exact = 0
        total_fuzzy = 0
        total_partial = 0
        
        for account, match_list in matches.items():
            account_matches = []
            exact_count = sum(1 for m in match_list if m.match_type == "exact")
            fuzzy_count = sum(1 for m in match_list if m.match_type == "fuzzy")
            partial_count = sum(1 for m in match_list if m.match_type == "partial")
            
            total_matches += len(match_list)
            total_exact += exact_count
            total_fuzzy += fuzzy_count
            total_partial += partial_count
            
            for match in match_list:
                account_matches.append({
                    "pdf_transaction": match.pdf_transaction,
                    "email_transaction": match.email_transaction,
                    "match_score": match.match_score,
                    "match_type": match.match_type
                })
            
            report["matches"][account] = account_matches
            report["reconciliation_summary"][account] = {
                "total_matches": len(match_list),
                "exact_matches": exact_count,
                "fuzzy_matches": fuzzy_count,
                "partial_matches": partial_count
            }
        
        report["reconciliation_summary"]["overall"] = {
            "total_matches": total_matches,
            "exact_matches": total_exact,
            "fuzzy_matches": total_fuzzy,
            "partial_matches": total_partial
        }
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def print_summary(self, report: Dict):
        """Print reconciliation summary"""
        print("\n" + "="*60)
        print("RECONCILIATION SUMMARY")
        print("="*60)
        
        overall = report["reconciliation_summary"]["overall"]
        print(f"Total Matches Found: {overall['total_matches']}")
        print(f"  - Exact Matches: {overall['exact_matches']}")
        print(f"  - Fuzzy Matches: {overall['fuzzy_matches']}")
        print(f"  - Partial Matches: {overall['partial_matches']}")
        
        print("\nBy Account:")
        for account, summary in report["reconciliation_summary"].items():
            if account != "overall":
                print(f"\n{account}:")
                print(f"  Total: {summary['total_matches']}")
                print(f"  Exact: {summary['exact_matches']}")
                print(f"  Fuzzy: {summary['fuzzy_matches']}")
                print(f"  Partial: {summary['partial_matches']}")

def main():
    """Main reconciliation function"""
    reconciler = StatementReconciler()
    
    # Paths
    statements_dir = "/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/statements"
    email_file = "/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/email_transactions.json"
    output_file = "/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/reconciliation_report.json"
    
    print("Starting Statement Reconciliation...")
    
    # Load data
    print("Loading PDF statements...")
    pdf_data = reconciler.load_pdf_statements(statements_dir)
    print(f"Loaded {len(pdf_data)} PDF statement groups")
    
    print("Loading email transactions...")
    email_data = reconciler.load_email_transactions(email_file)
    print(f"Loaded email transactions for {len(email_data)} banks")
    
    # Reconcile
    matches = reconciler.reconcile_statements(pdf_data, email_data)
    
    # Generate report
    report = reconciler.generate_reconciliation_report(matches, output_file)
    
    # Print summary
    reconciler.print_summary(report)
    
    print(f"\nDetailed reconciliation report saved to: {output_file}")

if __name__ == "__main__":
    main()
