import os
import google.auth
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load your specific credentials path
load_dotenv(r"C:\Users\shree\OneDrive\Documents\mynk\Credentials\apikeys.env.txt")

def list_gsc_properties():
    # Define the required scopes for GSC
    SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
    
    try:
        # Get Application Default Credentials (ADC)
        creds, project = google.auth.default(scopes=SCOPES)
        
        if not creds.valid:
            creds.refresh(Request())
            
        # Build the Search Console service
        service = build('searchconsole', 'v1', credentials=creds)
        
        # Execute the request to list sites
        site_list = service.sites().list().execute()
        
        print("\n" + "="*50)
        print("🔓 AUTHORIZED GOOGLE SEARCH CONSOLE PROPERTIES")
        print("="*50)
        
        if 'siteEntry' in site_list:
            for site in site_list['siteEntry']:
                print(f"✅ {site['siteUrl']} (Permission: {site['permissionLevel']})")
        else:
            print("❌ No properties found for these credentials.")
            
        print("="*50 + "\n")

    except Exception as e:
        print(f"❌ Error fetching properties: {e}")

if __name__ == "__main__":
    list_gsc_properties()