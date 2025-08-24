from credentials.enhanced_gmail_reader import GmailTransactionReader

def debug_hsbc_emails():
    """Debug HSBC emails to see their content"""
    reader = GmailTransactionReader()
    reader.authenticate()
    
    # Search for HSBC emails
    results = reader.service.users().messages().list(
        userId='me',
        labelIds=['INBOX'],
        q='from:hsbc@mail.hsbc.co.in',
        maxResults=5
    ).execute()

    messages = results.get('messages', [])
    print(f"📬 Found {len(messages)} HSBC messages")
    
    for i, msg in enumerate(messages[:3]):  # Check first 3 emails
        print(f"\n--- Email {i+1} ---")
        try:
            email_content = reader.get_email_content(msg['id'])
            print("📧 Email Content:")
            print(email_content[:500] + "..." if len(email_content) > 500 else email_content)
            
            # Try to parse
            transaction = reader.parse_hsbc_transaction(email_content)
            if transaction:
                print("✅ Parsed Transaction:", transaction)
            else:
                print("❌ Failed to parse transaction")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_hsbc_emails()
