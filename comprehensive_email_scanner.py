#!/usr/bin/env python3

import sys
import os
import re
import json
from collections import defaultdict, Counter
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from credentials.enhanced_gmail_reader import GmailTransactionReader, EMAIL_ACCOUNTS

def scan_all_financial_emails():
    """Comprehensive scan of all financial emails"""
    print("🚀 COMPREHENSIVE FINANCIAL EMAIL SCAN")
    print("=" * 50)
    
    all_financial_emails = defaultdict(list)
    
    for i, email_account in enumerate(EMAIL_ACCOUNTS, 1):
        print(f"\n[{i}/{len(EMAIL_ACCOUNTS)}] 📧 Scanning {email_account}...")
        
        try:
            reader = GmailTransactionReader(email_account)
            reader.authenticate()
            print("✅ Authentication successful")
            
            # Search queries for different types of financial emails
            search_queries = [
                'from:alerts.sbi.co.in OR from:sbi.co.in',
                'from:icicibank.com OR from:icici.com',
                'from:hdfcbank.com OR from:hdfc.com', 
                'from:kotak.com',
                'from:indusind.com',
                'from:canarabank.com OR from:canara.com',
                'from:axisbank.com OR from:axis.com',
                'credit card OR debit card',
                'transaction alert OR payment alert',
                'loan OR emi OR installment',
                'paytm OR phonepe OR gpay',
                'amazon OR flipkart OR zomato OR swiggy'
            ]
            
            account_emails = {}
            
            for j, query in enumerate(search_queries, 1):
                print(f"  [{j}/{len(search_queries)}] 🔍 Query: {query[:40]}...")
                
                try:
                    results = reader.service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=50
                    ).execute()
                    
                    messages = results.get('messages', [])
                    print(f"    📨 Found {len(messages)} emails")
                    
                    for k, message in enumerate(messages):
                        if k % 10 == 0 and k > 0:
                            print(f"    📊 Processing {k}/{len(messages)}...")
                        
                        try:
                            # Get email metadata and content
                            msg = reader.service.users().messages().get(
                                userId='me', id=message['id'], format='full'
                            ).execute()
                            
                            headers = msg['payload'].get('headers', [])
                            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                            
                            # Get email content
                            content = reader.get_email_content(message['id'])
                            
                            if is_financial_email(sender, subject, content):
                                domain = extract_domain(sender)
                                
                                email_data = {
                                    'sender': sender,
                                    'subject': subject,
                                    'date': date,
                                    'content': content[:2000],  # First 2000 chars
                                    'message_id': message['id'],
                                    'account': email_account
                                }
                                
                                if domain not in account_emails:
                                    account_emails[domain] = []
                                    print(f"    ✨ New institution: {domain}")
                                
                                account_emails[domain].append(email_data)
                                
                        except Exception as e:
                            continue
                    
                    time.sleep(0.2)  # Small delay between queries
                    
                except Exception as e:
                    print(f"    ❌ Query failed: {str(e)[:50]}...")
                    continue
            
            # Merge account emails into main collection
            for domain, emails in account_emails.items():
                all_financial_emails[domain].extend(emails)
            
            print(f"✅ {email_account} scan complete")
            print(f"   Found {len(account_emails)} institutions")
            
        except Exception as e:
            print(f"❌ Error scanning {email_account}: {str(e)[:50]}...")
            continue
    
    return dict(all_financial_emails)

def is_financial_email(sender, subject, content):
    """Check if email is financial"""
    text = f"{sender} {subject} {content}".lower()
    
    # Financial keywords
    keywords = [
        'transaction', 'payment', 'debit', 'credit', 'bank', 'card',
        'account', 'balance', 'amount', 'rupees', 'rs.', 'inr', '₹',
        'upi', 'neft', 'rtgs', 'imps', 'emi', 'loan', 'alert'
    ]
    
    # Must have at least 2 financial keywords
    keyword_count = sum(1 for keyword in keywords if keyword in text)
    
    # Or be from known financial domain
    financial_domains = [
        'bank', 'card', 'alerts', 'payment', 'paytm', 'phonepe'
    ]
    domain_match = any(domain in sender.lower() for domain in financial_domains)
    
    # Or have amount pattern
    amount_pattern = bool(re.search(r'(rs\.?|inr|₹)\s*[\d,]+', text, re.IGNORECASE))
    
    return keyword_count >= 2 or domain_match or amount_pattern

def extract_domain(sender):
    """Extract clean domain from sender"""
    match = re.search(r'@([^>]+)', sender)
    if match:
        domain = match.group(1).strip()
        # Clean up common patterns
        domain = re.sub(r'^(alerts?\.|noreply\.|donotreply\.)', '', domain)
        return domain
    return sender

def analyze_and_categorize(financial_emails):
    """Analyze and categorize all found emails"""
    print(f"\n🔬 ANALYZING {len(financial_emails)} FINANCIAL INSTITUTIONS")
    print("=" * 60)
    
    categories = {
        'banks': {},
        'credit_cards': {},
        'wallets': {},
        'ecommerce': {},
        'loans': {},
        'others': {}
    }
    
    for domain, emails in financial_emails.items():
        print(f"\n🏦 {domain.upper()} ({len(emails)} emails)")
        
        # Sample a few emails for analysis
        sample_emails = emails[:3]
        
        # Categorize
        category = categorize_institution(domain, sample_emails)
        categories[category][domain] = {
            'email_count': len(emails),
            'sample_subjects': [email['subject'] for email in sample_emails],
            'sample_senders': list(set([email['sender'] for email in sample_emails])),
            'sample_content': sample_emails[0]['content'] if sample_emails else '',
            'emails': sample_emails  # Keep samples for parser generation
        }
        
        print(f"  📂 Category: {category}")
        print(f"  📊 Sample subjects:")
        for subject in sample_emails[:2]:
            print(f"    • {subject['subject'][:70]}...")
    
    return categories

def categorize_institution(domain, sample_emails):
    """Categorize financial institution"""
    domain_lower = domain.lower()
    
    # Check sample content for better categorization
    all_text = ' '.join([
        f"{email.get('sender', '')} {email.get('subject', '')} {email.get('content', '')}"
        for email in sample_emails
    ]).lower()
    
    if any(keyword in domain_lower for keyword in ['bank', 'sbi', 'hdfc', 'icici', 'kotak', 'axis', 'indusind', 'canara', 'pnb']):
        if 'credit card' in all_text or 'card' in all_text:
            return 'credit_cards'
        elif 'loan' in all_text or 'emi' in all_text:
            return 'loans'
        else:
            return 'banks'
    elif any(keyword in domain_lower for keyword in ['card', 'visa', 'mastercard', 'amex']):
        return 'credit_cards'
    elif any(keyword in domain_lower for keyword in ['paytm', 'phonepe', 'gpay', 'mobikwik']):
        return 'wallets'
    elif any(keyword in domain_lower for keyword in ['amazon', 'flipkart', 'zomato', 'swiggy', 'uber', 'ola']):
        return 'ecommerce'
    elif 'loan' in all_text or 'emi' in all_text:
        return 'loans'
    else:
        return 'others'

def generate_parser_code(categories):
    """Generate parser code for each institution"""
    print(f"\n🤖 GENERATING PARSER CODE")
    print("=" * 30)
    
    parser_code = {}
    
    for category, institutions in categories.items():
        if not institutions:
            continue
            
        print(f"\n📂 {category.upper()}:")
        
        for domain, data in institutions.items():
            print(f"  🔧 Generating parser for {domain}...")
            
            # Analyze sample emails to create parser patterns
            sample_emails = data.get('emails', [])
            if not sample_emails:
                continue
            
            patterns = extract_patterns(sample_emails)
            code = generate_parser_function(domain, patterns, category)
            
            parser_code[domain] = {
                'category': category,
                'patterns': patterns,
                'code': code,
                'email_count': data['email_count']
            }
            
            print(f"    ✅ Generated {len(patterns)} patterns")
    
    return parser_code

def extract_patterns(sample_emails):
    """Extract transaction patterns from sample emails"""
    patterns = []
    
    for email in sample_emails:
        content = email.get('content', '')
        
        # Amount patterns
        amounts = re.findall(r'(amount|rs\.?|inr|₹)\s*:?\s*([\d,]+\.?\d*)', content, re.IGNORECASE)
        if amounts:
            patterns.append({
                'type': 'amount',
                'pattern': r'(amount|rs\.?|inr|₹)\s*:?\s*([\d,]+\.?\d*)',
                'sample': amounts[0]
            })
        
        # Account patterns
        accounts = re.findall(r'(account|a/c|card).*?(\d{4,})', content, re.IGNORECASE)
        if accounts:
            patterns.append({
                'type': 'account',
                'pattern': r'(account|a/c|card).*?(\d{4,})',
                'sample': accounts[0]
            })
        
        # Date patterns
        dates = re.findall(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', content)
        if dates:
            patterns.append({
                'type': 'date',
                'pattern': r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                'sample': dates[0]
            })
    
    # Remove duplicates
    unique_patterns = []
    seen_types = set()
    for pattern in patterns:
        if pattern['type'] not in seen_types:
            unique_patterns.append(pattern)
            seen_types.add(pattern['type'])
    
    return unique_patterns

def generate_parser_function(domain, patterns, category):
    """Generate parser function code"""
    bank_name = domain.split('.')[0].upper().replace('-', '_')
    
    code = f'''def parse_{bank_name.lower()}_transaction(self, email_content: str) -> Optional[Dict]:
    """Parse {bank_name} {category} emails"""
    transaction = {{
        'bank': '{bank_name}',
        'raw_content': email_content
    }}
    
'''
    
    for pattern in patterns:
        code += f'''    # {pattern['type'].title()} pattern
    {pattern['type']}_match = re.search(r'{pattern['pattern']}', email_content, re.IGNORECASE)
    if {pattern['type']}_match:
        # Process {pattern['type']} - sample: {pattern['sample']}
        pass
    
'''
    
    code += '''    return transaction if transaction.get('amount') else None'''
    
    return code

def main():
    print("🚀 STARTING COMPREHENSIVE EMAIL SCAN")
    start_time = time.time()
    
    # Scan all financial emails
    financial_emails = scan_all_financial_emails()
    
    if not financial_emails:
        print("❌ No financial emails found!")
        return
    
    print(f"\n🎉 SCAN COMPLETE!")
    print(f"⏱️  Time taken: {time.time() - start_time:.1f} seconds")
    print(f"🏦 Found {len(financial_emails)} financial institutions")
    
    # Analyze and categorize
    categories = analyze_and_categorize(financial_emails)
    
    # Generate parser code
    parser_code = generate_parser_code(categories)
    
    # Save results
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    
    # Save raw email data
    with open(f'financial_emails_{timestamp}.json', 'w') as f:
        json.dump(financial_emails, f, indent=2, default=str)
    
    # Save categorized analysis
    with open(f'financial_analysis_{timestamp}.json', 'w') as f:
        json.dump(categories, f, indent=2, default=str)
    
    # Save parser code
    with open(f'parser_code_{timestamp}.json', 'w') as f:
        json.dump(parser_code, f, indent=2, default=str)
    
    print(f"\n💾 RESULTS SAVED:")
    print(f"  📧 financial_emails_{timestamp}.json")
    print(f"  📊 financial_analysis_{timestamp}.json") 
    print(f"  🤖 parser_code_{timestamp}.json")
    
    # Print summary
    print(f"\n📈 SUMMARY:")
    for category, institutions in categories.items():
        if institutions:
            print(f"  {category.upper()}: {len(institutions)} institutions")
            for domain in institutions.keys():
                print(f"    • {domain}")

if __name__ == "__main__":
    main()
