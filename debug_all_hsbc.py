from credentials.enhanced_gmail_reader import GmailTransactionReader

def debug_all_hsbc_emails():
    """Debug all HSBC emails to find different sender addresses"""
    reader = GmailTransactionReader()
    reader.authenticate()
    
    # Search for all HSBC emails (broader search)
    queries = [
        'from:hsbc@mail.hsbc.co.in',
        'from:alerts@mail.hsbc.co.in', 
        'from:hsbc',
        'subject:hsbc'
    ]
    
    all_messages = set()
    
    for query in queries:
        print(f"\n🔍 Searching: {query}")
        results = reader.service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            q=query,
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        print(f"Found {len(messages)} messages")
        
        for msg in messages:
            all_messages.add(msg['id'])
    
    print(f"\n📬 Total unique HSBC messages: {len(all_messages)}")
    
    # Check first few messages
    for i, msg_id in enumerate(list(all_messages)[:5]):
        print(f"\n--- Message {i+1} ---")
        try:
            # Get message details
            msg_data = reader.service.users().messages().get(userId='me', id=msg_id).execute()
            
            # Get sender
            headers = msg_data['payload'].get('headers', [])
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            
            # Get content and try to parse
            email_content = reader.get_email_content(msg_id)
            transaction = reader.parse_hsbc_transaction(email_content)
            
            if transaction:
                print("✅ Parsed Transaction:", transaction)
            else:
                print("❌ Failed to parse")
                # Show first 200 chars of content for debugging
                print(f"Content preview: {email_content[:200]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_all_hsbc_emails()
