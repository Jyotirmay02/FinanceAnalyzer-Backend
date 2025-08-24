from __future__ import print_function
import os.path
import re
import base64
import google.auth.transport.requests
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# If modifying scopes, delete the token.json file
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "/Users/jmysethi/Downloads/client_secret_885429144379-als8fusnv1vqdo3oosna9j3glp77ckm5.apps.googleusercontent.com.json"

def authenticate():
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid creds, ask user to login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(google.auth.transport.requests.Request())
            except RefreshError:
                print("⚠️ Refresh token expired, logging in again…")
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save creds for next run
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return creds

def get_hsbc_transactions(creds: Credentials):
    service = build('gmail', 'v1', credentials=creds)

    # Search only for HSBC emails in inbox
    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX'],
        q='from:hsbc@mail.hsbc.co.in'
    ).execute()

    messages = results.get('messages', [])
    if not messages:
        print("📭 No HSBC transaction emails found.")
        return

    print(f"📬 Found {len(messages)} HSBC messages. Showing latest 5:\n")
    for msg in messages[:5]:  # limit to 5 for now
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        payload = msg_data['payload']
        parts = payload.get('parts', [])
        data = ""

        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        else:
            if 'data' in payload['body']:
                data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        if not data.strip():
            continue


        # Extract transaction details with updated regex
        card_match = re.search(r'ending with (\d{4})', data)
        amt_match = re.search(r'INR\s*([\d,]+\.\d{2})', data)  # allows optional space after INR
        merchant_match = re.search(r'payment to ([A-Z0-9 &]+?) on', data)  # matches uppercase letters, numbers, & spaces
        date_match = re.search(r'on (\d{1,2} \w+ \d{4}) at', data)
        time_match = re.search(r'at (\d{2}:\d{2})', data)

        transaction = {
            "card_last4": card_match.group(1) if card_match else None,
            "amount": amt_match.group(1) if amt_match else None,
            "merchant": merchant_match.group(1) if merchant_match else None,
            "date": date_match.group(1) if date_match else None,
            "time": time_match.group(1) if time_match else None
        }

        print("🔹 Transaction Found:", transaction)

def main():
    creds = authenticate()

    # Optional: list labels
    service = build("gmail", "v1", credentials=creds)
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    print("✅ Gmail Connected. Labels available:")
    for label in labels:
        print(f"- {label['name']}")

    print("\n--- HSBC Transactions ---")
    get_hsbc_transactions(creds)

if __name__ == "__main__":
    main()
