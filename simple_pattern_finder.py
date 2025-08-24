#!/usr/bin/env python3

import sys
import os
import re
import json
from collections import defaultdict, Counter
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from credentials.enhanced_gmail_reader import GmailTransactionReader, EMAIL_ACCOUNTS

def find_financial_senders():
    """Quick scan to find all financial email senders"""
    print("🔍 Starting financial email sender discovery...")
    print(f"📧 Will analyze {len(EMAIL_ACCOUNTS)} Gmail accounts")
    
    all_senders = set()
    
    for i, email_account in enumerate(EMAIL_ACCOUNTS, 1):
        print(f"\n[{i}/{len(EMAIL_ACCOUNTS)}] 🔑 Authenticating {email_account}...")
        
        try:
            reader = GmailTransactionReader(email_account)
            reader.authenticate()
            print(f"✅ Authentication successful for {email_account}")
            
            # Search for emails with financial keywords
            financial_queries = [
                'transaction OR debit OR credit OR payment',
                'bank OR card OR account OR balance', 
                'rupees OR rs OR inr OR amount',
                'upi OR neft OR rtgs OR imps OR atm'
            ]
            
            account_senders = set()
            
            for j, query in enumerate(financial_queries, 1):
                print(f"  [{j}/{len(financial_queries)}] 🔍 Searching: '{query[:30]}...'")
                
                try:
                    results = reader.service.users().messages().list(
                        userId='me',
                        labelIds=['INBOX'],
                        q=query,
                        maxResults=100
                    ).execute()
                    
                    messages = results.get('messages', [])
                    print(f"    📨 Found {len(messages)} matching emails")
                    
                    for k, message in enumerate(messages[:20]):  # Check first 20
                        if k % 5 == 0 and k > 0:
                            print(f"    📊 Processed {k}/20 emails...")
                            
                        try:
                            msg = reader.service.users().messages().get(
                                userId='me', id=message['id'], format='metadata'
                            ).execute()
                            
                            headers = msg['payload'].get('headers', [])
                            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                            
                            if sender and self._is_financial_sender(sender, subject):
                                # Extract domain
                                domain_match = re.search(r'@([^>]+)', sender)
                                if domain_match:
                                    domain = domain_match.group(1).strip()
                                    sender_info = (domain, sender, subject)
                                    if sender_info not in account_senders:
                                        account_senders.add(sender_info)
                                        print(f"    ✨ New sender found: {domain}")
                                        
                        except Exception as e:
                            continue
                    
                    print(f"    ✅ Query complete. Found {len(account_senders)} unique senders so far")
                    time.sleep(0.5)  # Small delay to avoid rate limits
                            
                except Exception as e:
                    print(f"    ❌ Error with query '{query[:20]}...': {str(e)[:50]}...")
                    continue
            
            all_senders.update(account_senders)
            print(f"✅ {email_account} complete. Total unique senders: {len(all_senders)}")
                    
        except Exception as e:
            print(f"❌ Error with {email_account}: {str(e)[:50]}...")
            continue
    
    print(f"\n🎉 Discovery complete! Found {len(all_senders)} unique financial senders")
    return all_senders

def _is_financial_sender(sender, subject):
    """Check if sender is financial institution"""
    text = f"{sender} {subject}".lower()
    
    financial_keywords = [
        'bank', 'card', 'payment', 'transaction', 'debit', 'credit',
        'account', 'balance', 'alert', 'notification', 'statement'
    ]
    
    financial_domains = [
        'kotak', 'hdfc', 'icici', 'sbi', 'axis', 'indusind', 'pnb',
        'paytm', 'phonepe', 'gpay', 'amazon', 'flipkart', 'visa', 'mastercard'
    ]
    
    keyword_match = any(keyword in text for keyword in financial_keywords)
    domain_match = any(domain in text for domain in financial_domains)
    
    return keyword_match or domain_match

def categorize_senders(senders):
    """Categorize senders by institution type"""
    print(f"\n🏦 Categorizing {len(senders)} unique senders...")
    
    categories = {
        'banks': [],
        'credit_cards': [],
        'wallets': [],
        'ecommerce': [],
        'others': []
    }
    
    bank_keywords = ['bank', 'sbi', 'hdfc', 'icici', 'kotak', 'axis', 'indusind', 'pnb', 'canara', 'union', 'bob']
    card_keywords = ['card', 'visa', 'mastercard', 'amex', 'credit', 'rupay']
    wallet_keywords = ['paytm', 'phonepe', 'gpay', 'mobikwik', 'freecharge', 'amazon pay', 'upi']
    ecommerce_keywords = ['amazon', 'flipkart', 'myntra', 'zomato', 'swiggy', 'uber', 'ola', 'bigbasket']
    
    for domain, sender, subject in senders:
        domain_lower = domain.lower()
        sender_lower = sender.lower()
        
        if any(keyword in domain_lower or keyword in sender_lower for keyword in bank_keywords):
            categories['banks'].append((domain, sender, subject))
            print(f"  🏦 Bank: {domain}")
        elif any(keyword in domain_lower or keyword in sender_lower for keyword in card_keywords):
            categories['credit_cards'].append((domain, sender, subject))
            print(f"  💳 Card: {domain}")
        elif any(keyword in domain_lower or keyword in sender_lower for keyword in wallet_keywords):
            categories['wallets'].append((domain, sender, subject))
            print(f"  📱 Wallet: {domain}")
        elif any(keyword in domain_lower or keyword in sender_lower for keyword in ecommerce_keywords):
            categories['ecommerce'].append((domain, sender, subject))
            print(f"  🛒 E-commerce: {domain}")
        else:
            categories['others'].append((domain, sender, subject))
            print(f"  ❓ Other: {domain}")
    
    return categories

def print_results(categories):
    """Print categorized results"""
    print("\n" + "="*60)
    print("📊 FINANCIAL EMAIL SENDERS DISCOVERED:")
    print("="*60)
    
    total_senders = sum(len(senders) for senders in categories.values())
    print(f"🎯 Total: {total_senders} unique financial institutions found!")
    
    for category, senders in categories.items():
        if senders:
            print(f"\n🏷️  {category.upper()} ({len(senders)} institutions):")
            
            # Group by domain
            domain_groups = defaultdict(list)
            for domain, sender, subject in senders:
                domain_groups[domain].append((sender, subject))
            
            for domain, sender_list in sorted(domain_groups.items()):
                print(f"  📧 {domain} ({len(sender_list)} emails)")
                for sender, subject in sender_list[:2]:  # Show first 2 subjects
                    print(f"    • {subject[:60]}...")

def main():
    print("🚀 STARTING FINANCIAL EMAIL PATTERN DISCOVERY")
    print("=" * 50)
    start_time = time.time()
    
    # Find all financial senders
    senders = find_financial_senders()
    
    if not senders:
        print("❌ No financial emails found!")
        return
    
    # Categorize senders
    print(f"\n⏱️  Discovery took {time.time() - start_time:.1f} seconds")
    categories = categorize_senders(senders)
    
    # Print results
    print_results(categories)
    
    # Save results
    print(f"\n💾 Saving results...")
    results = {}
    for category, senders in categories.items():
        results[category] = [{'domain': domain, 'sender': sender, 'sample_subject': subject} 
                           for domain, sender, subject in senders]
    
    with open('financial_senders.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Results saved to financial_senders.json")
    print(f"🎉 ANALYSIS COMPLETE! Found {len(senders)} financial institutions")
    print(f"⏱️  Total time: {time.time() - start_time:.1f} seconds")

if __name__ == "__main__":
    main()
