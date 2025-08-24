from __future__ import print_function
import os.path
import pickle
import base64
import re
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText

# If modifying these SCOPES, delete the token files.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# ✅ List of accounts you want to support
# You will need to authenticate once for each account (tokens will be saved separately)
EMAIL_ACCOUNTS = [
    "jyotirmays123@gmail.com",
    "jotirmays123@gmail.com"
]

CREDENTIALS_DIR = "/Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend/credentials"

def authenticate_gmail(user_email):
    """Authenticate a Gmail user and return the service object."""
    creds = None
    token_file = os.path.join(CREDENTIALS_DIR, f"token_{user_email}.pickle")

    # Load credentials from pickle if available
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # If no creds or invalid, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Each user must go through consent screen once
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(CREDENTIALS_DIR, "credentials.json"), SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save credentials for this user
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    # Build Gmail API service
    return build('gmail', 'v1', credentials=creds)


def read_latest_email(service, user_email):
    """Read the latest email from inbox of a given account."""
    try:
        results = service.users().messages().list(userId='me', maxResults=1, labelIds=['INBOX']).execute()
        messages = results.get('messages', [])

        if not messages:
            print(f"No messages found for {user_email}")
            return None

        msg_id = messages[0]['id']
        msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        payload = msg['payload']
        headers = payload['headers']

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "")
        snippet = msg.get('snippet', "")

        print(f"\n📧 Email for {user_email}")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Snippet: {snippet}")
        return {"from": sender, "subject": subject, "snippet": snippet}

    except Exception as e:
        print(f"An error occurred for {user_email}: {e}")
        return None


if __name__ == '__main__':
    for email in EMAIL_ACCOUNTS:
        print(f"\n🔑 Authenticating {email}...")
        service = authenticate_gmail(email)
        read_latest_email(service, email)
