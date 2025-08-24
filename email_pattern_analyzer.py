#!/usr/bin/env python3

import sys
import os
import re
import json
from collections import defaultdict, Counter
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from credentials.enhanced_gmail_reader import GmailTransactionReader

class EmailPatternAnalyzer:
    def __init__(self, user_email: str):
        self.reader = GmailTransactionReader(user_email)
        self.financial_keywords = [
            'transaction', 'debit', 'credit', 'payment', 'transfer', 'withdrawal',
            'deposit', 'balance', 'account', 'card', 'bank', 'amount', 'rupees',
            'rs.', 'inr', 'upi', 'neft', 'rtgs', 'imps', 'emi', 'loan', 'atm'
        ]
        
    def scan_financial_emails(self, limit: int = 500) -> dict:
        """Scan emails for financial transaction patterns"""
        print(f"🔍 Scanning {limit} emails for financial patterns...")
        
        # Get recent emails
        results = self.reader.service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        financial_emails = defaultdict(list)
        sender_patterns = Counter()
        
        for i, message in enumerate(messages):
            if i % 50 == 0:
                print(f"  Processed {i}/{len(messages)} emails...")
                
            try:
                msg = self.reader.service.users().messages().get(
                    userId='me', id=message['id'], format='full'
                ).execute()
                
                # Extract sender and subject
                headers = msg['payload'].get('headers', [])
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                
                # Get email content
                content = self.reader.get_email_content(message['id'])
                
                # Check if it's a financial email
                if self._is_financial_email(sender, subject, content):
                    sender_domain = self._extract_domain(sender)
                    financial_emails[sender_domain].append({
                        'sender': sender,
                        'subject': subject,
                        'content': content[:1000],  # First 1000 chars
                        'message_id': message['id']
                    })
                    sender_patterns[sender_domain] += 1
                    
            except Exception as e:
                continue
                
        print(f"✅ Found {sum(sender_patterns.values())} financial emails from {len(sender_patterns)} institutions")
        return dict(financial_emails), dict(sender_patterns)
    
    def _is_financial_email(self, sender: str, subject: str, content: str) -> bool:
        """Check if email is financial transaction related"""
        text = f"{sender} {subject} {content}".lower()
        
        # Check for financial keywords
        keyword_count = sum(1 for keyword in self.financial_keywords if keyword in text)
        
        # Check for known financial domains
        financial_domains = [
            'bank', 'kotak', 'hdfc', 'icici', 'sbi', 'axis', 'indusind',
            'paytm', 'phonepe', 'gpay', 'amazon', 'flipkart', 'visa', 'mastercard',
            'alerts', 'notification', 'statement'
        ]
        
        domain_match = any(domain in sender.lower() for domain in financial_domains)
        
        # Check for amount patterns
        amount_pattern = bool(re.search(r'(rs\.?|inr|₹)\s*[\d,]+', text, re.IGNORECASE))
        
        return keyword_count >= 2 or domain_match or amount_pattern
    
    def _extract_domain(self, sender: str) -> str:
        """Extract domain from sender email"""
        match = re.search(r'@([^>]+)', sender)
        if match:
            return match.group(1).strip()
        return sender
    
    def analyze_patterns(self, financial_emails: dict) -> dict:
        """Analyze patterns for each financial institution"""
        print("\n🔬 Analyzing transaction patterns...")
        
        patterns = {}
        
        for domain, emails in financial_emails.items():
            if len(emails) < 2:  # Skip domains with too few emails
                continue
                
            print(f"\n📧 Analyzing {domain} ({len(emails)} emails):")
            
            # Analyze common patterns
            subjects = [email['subject'] for email in emails]
            contents = [email['content'] for email in emails]
            
            # Find common subject patterns
            subject_patterns = self._find_common_patterns(subjects)
            
            # Find amount patterns
            amount_patterns = []
            for content in contents:
                amounts = re.findall(r'(rs\.?|inr|₹)\s*([\d,]+\.?\d*)', content, re.IGNORECASE)
                if amounts:
                    amount_patterns.extend(amounts)
            
            # Find account patterns
            account_patterns = []
            for content in contents:
                accounts = re.findall(r'(account|a/c|card).*?(\d{4,})', content, re.IGNORECASE)
                if accounts:
                    account_patterns.extend(accounts)
            
            patterns[domain] = {
                'email_count': len(emails),
                'sample_subjects': subjects[:3],
                'sample_content': contents[0][:500] if contents else '',
                'subject_patterns': subject_patterns,
                'amount_patterns': list(set(amount_patterns)),
                'account_patterns': list(set(account_patterns)),
                'sample_emails': emails[:2]  # Keep 2 sample emails for analysis
            }
            
            print(f"  📊 {len(subject_patterns)} subject patterns found")
            print(f"  💰 {len(set(amount_patterns))} amount patterns found")
            
        return patterns
    
    def _find_common_patterns(self, texts: list) -> list:
        """Find common patterns in text list"""
        if not texts:
            return []
            
        # Simple pattern detection - find common words/phrases
        word_counts = Counter()
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            word_counts.update(words)
        
        # Return most common words that appear in multiple texts
        common_patterns = [word for word, count in word_counts.most_common(10) if count > 1]
        return common_patterns
    
    def generate_parser_suggestions(self, patterns: dict) -> dict:
        """Generate parser logic suggestions for each institution"""
        print("\n🤖 Generating parser suggestions...")
        
        suggestions = {}
        
        for domain, pattern_data in patterns.items():
            print(f"\n🏦 {domain}:")
            
            # Analyze sample emails to suggest regex patterns
            sample_emails = pattern_data.get('sample_emails', [])
            
            parser_suggestions = {
                'domain': domain,
                'email_count': pattern_data['email_count'],
                'suggested_patterns': [],
                'sample_code': ''
            }
            
            # Generate regex patterns based on content analysis
            for email in sample_emails[:2]:  # Analyze first 2 emails
                content = email['content']
                
                # Look for transaction patterns
                transaction_patterns = self._extract_transaction_patterns(content)
                parser_suggestions['suggested_patterns'].extend(transaction_patterns)
            
            # Generate sample parser code
            parser_suggestions['sample_code'] = self._generate_sample_parser(domain, parser_suggestions['suggested_patterns'])
            
            suggestions[domain] = parser_suggestions
            
            print(f"  ✅ Generated {len(parser_suggestions['suggested_patterns'])} pattern suggestions")
        
        return suggestions
    
    def _extract_transaction_patterns(self, content: str) -> list:
        """Extract potential transaction patterns from content"""
        patterns = []
        
        # Amount patterns
        amount_matches = re.findall(r'(amount|rs\.?|inr|₹)\s*:?\s*([\d,]+\.?\d*)', content, re.IGNORECASE)
        if amount_matches:
            patterns.append({
                'type': 'amount',
                'pattern': r'(amount|rs\.?|inr|₹)\s*:?\s*([\d,]+\.?\d*)',
                'description': 'Transaction amount'
            })
        
        # Account patterns
        account_matches = re.findall(r'(account|a/c|card).*?(\d{4,})', content, re.IGNORECASE)
        if account_matches:
            patterns.append({
                'type': 'account',
                'pattern': r'(account|a/c|card).*?(\d{4,})',
                'description': 'Account number'
            })
        
        # Date patterns
        date_matches = re.findall(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', content)
        if date_matches:
            patterns.append({
                'type': 'date',
                'pattern': r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                'description': 'Transaction date'
            })
        
        # Reference patterns
        ref_matches = re.findall(r'(ref|reference|utr|txn).*?([a-z0-9]+)', content, re.IGNORECASE)
        if ref_matches:
            patterns.append({
                'type': 'reference',
                'pattern': r'(ref|reference|utr|txn).*?([a-z0-9]+)',
                'description': 'Reference number'
            })
        
        return patterns
    
    def _generate_sample_parser(self, domain: str, patterns: list) -> str:
        """Generate sample parser code"""
        bank_name = domain.split('.')[0].upper()
        
        code = f'''def parse_{bank_name.lower()}_transaction(self, email_content: str) -> Optional[Dict]:
    """Parse {bank_name} transaction emails"""
    transaction = {{
        'bank': '{bank_name}',
        'raw_content': email_content
    }}
    
'''
        
        for i, pattern in enumerate(patterns[:3]):  # Max 3 patterns
            code += f'''    # Pattern {i+1}: {pattern['description']}
    {pattern['type']}_match = re.search(r'{pattern['pattern']}', email_content, re.IGNORECASE)
    if {pattern['type']}_match:
        # Extract and process {pattern['type']}
        pass
    
'''
        
        code += '''    return transaction if transaction.get('amount') else None'''
        
        return code

def main():
    """Main function to analyze email patterns"""
    from credentials.enhanced_gmail_reader import EMAIL_ACCOUNTS
    
    all_patterns = {}
    all_suggestions = {}
    
    for email_account in EMAIL_ACCOUNTS:
        print(f"\n🔑 Analyzing {email_account}...")
        
        analyzer = EmailPatternAnalyzer(email_account)
        analyzer.reader.authenticate()
        
        # Scan for financial emails
        financial_emails, sender_stats = analyzer.scan_financial_emails(limit=300)
        
        # Analyze patterns
        patterns = analyzer.analyze_patterns(financial_emails)
        
        # Generate parser suggestions
        suggestions = analyzer.generate_parser_suggestions(patterns)
        
        all_patterns[email_account] = patterns
        all_suggestions[email_account] = suggestions
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with open(f'email_patterns_{timestamp}.json', 'w') as f:
        json.dump(all_patterns, f, indent=2, default=str)
    
    with open(f'parser_suggestions_{timestamp}.json', 'w') as f:
        json.dump(all_suggestions, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to:")
    print(f"  📊 email_patterns_{timestamp}.json")
    print(f"  🤖 parser_suggestions_{timestamp}.json")
    
    # Print summary
    print(f"\n📈 SUMMARY:")
    total_institutions = sum(len(patterns) for patterns in all_patterns.values())
    print(f"  🏦 Found {total_institutions} financial institutions")
    
    for email, patterns in all_patterns.items():
        print(f"\n📧 {email}:")
        for domain, data in patterns.items():
            print(f"  • {domain}: {data['email_count']} emails")

if __name__ == "__main__":
    main()
