from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from credentials.enhanced_gmail_reader import GmailTransactionReader

class EmailTransactionService:
    def __init__(self):
        self.gmail_reader = GmailTransactionReader()
        
    def fetch_email_transactions(self) -> Dict[str, List[Dict]]:
        """Fetch transactions from email sources"""
        try:
            self.gmail_reader.authenticate()
            return self.gmail_reader.get_all_bank_transactions()
        except Exception as e:
            print(f"❌ Error fetching email transactions: {e}")
            return {}
    
    def convert_to_standard_format(self, email_transactions: Dict[str, List[Dict]]) -> List[Dict]:
        """Convert email transactions to standard transaction format"""
        standard_transactions = []
        
        for bank, transactions in email_transactions.items():
            for transaction in transactions:
                # Convert to standard format matching your existing transaction model
                standard_transaction = {
                    'id': f"email_{transaction.get('email_id', '')}_{len(standard_transactions)}",
                    'date': transaction.get('date', ''),
                    'description': f"{transaction.get('merchant', 'Unknown Merchant')} - {bank} Card",
                    'amount': -abs(transaction.get('amount', 0)),  # Negative for expenses
                    'balance': None,  # Email transactions don't have balance info
                    'category': self.categorize_transaction(transaction.get('merchant', '')),
                    'bank': bank,
                    'source': 'email',
                    'card_last4': transaction.get('card_last4'),
                    'transaction_time': transaction.get('time'),
                    'reference': transaction.get('reference')
                }
                standard_transactions.append(standard_transaction)
                
        return standard_transactions
    
    def categorize_transaction(self, merchant: str) -> str:
        """Basic categorization based on merchant name"""
        merchant_lower = merchant.lower()
        
        # Simple categorization rules
        if any(word in merchant_lower for word in ['swiggy', 'zomato', 'restaurant', 'food', 'cafe']):
            return 'Food & Dining'
        elif any(word in merchant_lower for word in ['amazon', 'flipkart', 'shopping', 'store']):
            return 'Shopping'
        elif any(word in merchant_lower for word in ['uber', 'ola', 'taxi', 'transport']):
            return 'Transportation'
        elif any(word in merchant_lower for word in ['petrol', 'fuel', 'gas', 'hp', 'ioc']):
            return 'Fuel'
        elif any(word in merchant_lower for word in ['medical', 'pharmacy', 'hospital', 'doctor']):
            return 'Healthcare'
        elif any(word in merchant_lower for word in ['movie', 'cinema', 'entertainment']):
            return 'Entertainment'
        else:
            return 'Others'
    
    def create_email_transactions_dataframe(self, transactions: List[Dict]) -> pd.DataFrame:
        """Create pandas DataFrame from email transactions"""
        if not transactions:
            return pd.DataFrame()
            
        df = pd.DataFrame(transactions)
        
        # Convert date column to datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
        # Sort by date
        df = df.sort_values('date', ascending=False)
        
        return df
    
    def merge_with_existing_data(self, existing_df: pd.DataFrame, email_transactions: List[Dict]) -> pd.DataFrame:
        """Merge email transactions with existing transaction data"""
        if not email_transactions:
            return existing_df
            
        email_df = self.create_email_transactions_dataframe(email_transactions)
        
        if existing_df.empty:
            return email_df
            
        # Combine dataframes
        combined_df = pd.concat([existing_df, email_df], ignore_index=True)
        
        # Remove duplicates based on description, amount, and date
        combined_df = combined_df.drop_duplicates(
            subset=['date', 'description', 'amount'], 
            keep='first'
        )
        
        # Sort by date
        combined_df = combined_df.sort_values('date', ascending=False)
        
        return combined_df
    
    def get_email_transaction_summary(self, transactions: List[Dict]) -> Dict:
        """Generate summary statistics for email transactions"""
        if not transactions:
            return {
                'total_transactions': 0,
                'total_amount': 0,
                'categories': {},
                'banks': {}
            }
            
        df = self.create_email_transactions_dataframe(transactions)
        
        summary = {
            'total_transactions': len(df),
            'total_amount': abs(df['amount'].sum()),
            'categories': df.groupby('category')['amount'].agg(['count', 'sum']).abs().to_dict(),
            'banks': df.groupby('bank')['amount'].agg(['count', 'sum']).abs().to_dict(),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d') if not df.empty else None,
                'end': df['date'].max().strftime('%Y-%m-%d') if not df.empty else None
            }
        }
        
        return summary

# Example usage
def main():
    service = EmailTransactionService()
    
    # Fetch email transactions
    print("📧 Fetching email transactions...")
    email_transactions = service.fetch_email_transactions()
    
    # Convert to standard format
    standard_transactions = service.convert_to_standard_format(email_transactions)
    
    # Create DataFrame
    df = service.create_email_transactions_dataframe(standard_transactions)
    print(f"📊 Created DataFrame with {len(df)} transactions")
    
    # Generate summary
    summary = service.get_email_transaction_summary(standard_transactions)
    print(f"💰 Total Amount: ₹{summary['total_amount']:,.2f}")
    print(f"📅 Date Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    
    # Save to CSV for testing
    if not df.empty:
        df.to_csv('email_transactions.csv', index=False)
        print("💾 Saved to email_transactions.csv")

if __name__ == "__main__":
    main()
