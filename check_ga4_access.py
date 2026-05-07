import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load your specific credentials path
load_dotenv(r"C:\Users\shree\OneDrive\Documents\mynk\Credentials\apikeys.env.txt")

def list_ga4_properties():
    # Scopes required for GA4 Admin API
    SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
    
    try:
        # 1. Load credentials from your local token.json
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        else:
            print("❌ token.json not found. Please run your authentication flow first.")
            return

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        
        # 2. Build the Analytics Admin Service
        # Note: GA4 uses the Analytics Admin API v1alpha or v1beta
        service = build('analyticsadmin', 'v1alpha', credentials=creds)
        
        print("\n" + "="*60)
        print("📊 AUTHORIZED GA4 PROPERTIES & IDs")
        print("="*60)
        
        # 3. List Accounts first
        accounts = service.accounts().list().execute()
        
        if 'accounts' in accounts:
            for account in accounts['accounts']:
                account_id = account['name']
                print(f"\n📂 Account: {account['displayName']} ({account_id})")
                
                # 4. List Properties under each account
                properties = service.properties().list(filter=f"parent:{account_id}").execute()
                
                if 'properties' in properties:
                    for prop in properties['properties']:
                        # The 'name' field is 'properties/123456789'
                        prop_id = prop['name'].split('/')[-1]
                        print(f"   ✅ {prop['displayName']} | ID: {prop_id}")
                else:
                    print("   ⚠️ No properties found in this account.")
        else:
            print("❌ No Analytics accounts found for these credentials.")
            
        print("\n" + "="*60 + "\n")

    except Exception as e:
        print(f"❌ Error fetching GA4 data: {e}")

if __name__ == "__main__":
    list_ga4_properties()