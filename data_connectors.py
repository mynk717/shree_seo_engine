import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from shopify_token_manager import get_validated_token

# Google Auth Imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- FOOLPROOF ENV LOADER ---
base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(base_dir, ".env")):
    load_dotenv(os.path.join(base_dir, ".env"))
elif os.path.exists(os.path.join(base_dir, ".env.txt")):
    load_dotenv(os.path.join(base_dir, ".env.txt"))
else:
    # Fallback to your old master credentials folder just in case!
    load_dotenv(r"C:\Users\shree\OneDrive\Documents\mynk\Credentials\apikeys.env.txt")

# Load variables
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID")
GSC_PROPERTY = "sc-domain:shreeshivam.com"

# Combined Scopes for both GSC and GA4
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/analytics.readonly'
]

def get_google_credentials():
    """Authenticates via browser popup (client_secret.json) and saves token.json."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This triggers the browser login that works for your test account
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def get_notion_seo_edits():
    """Fetches the SEO Edit logs from Notion using the correct schema names."""
    notion_token = os.getenv("NOTION_TOKEN")
    # Using the correct .env variable name
    db_id = os.getenv("NOTION_DB_SEO_EDITS", "34ccbec2-7659-81e3-978c-dfd1d247a437")
    
    if not notion_token or not db_id:
        print("Missing Notion credentials for Edits DB.")
        return pd.DataFrame()
        
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            results = response.json().get('results', [])
            rows = []
            
            for page in results:
                props = page.get('properties', {})
                
                title_arr = props.get("Page / URL", {}).get("title", [])
                page_url = title_arr[0].get("plain_text", "") if title_arr else ""
                
                date_obj = props.get("Changed On", {}).get("date", {})
                changed_on = date_obj.get("start", None) if date_obj else None
                
                notes_arr = props.get("Notes", {}).get("rich_text", [])
                notes = notes_arr[0].get("plain_text", "") if notes_arr else ""
                
                status_obj = props.get("Status", {}).get("select", {})
                status = status_obj.get("name", "") if status_obj else ""

                rows.append({
                    "Date": changed_on,
                    "Status": status,
                    "Page / URL": page_url,
                    "Notes / Action": notes
                })
                
            return pd.DataFrame(rows)
        else:
            print(f"Notion Fetch Error: {response.text}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Failed to fetch Notion Edits: {e}")
        return pd.DataFrame()

def get_gsc_page_data(days=30):
    """Fetches GSC data AND the Top Query for each URL."""
    try:
        creds = get_google_credentials()
        service = build('searchconsole', 'v1', credentials=creds)
        
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

        # We request BOTH page and query dimensions
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['page', 'query'],
            'rowLimit': 10000 # Increased limit to handle query variants
        }
        
        response = service.searchanalytics().query(siteUrl=GSC_PROPERTY, body=request).execute()
        
        # We need to process this so we only keep the TOP query for each page
        page_data = {}
        
        if 'rows' in response:
            for row in response['rows']:
                full_url = row['keys'][0]
                query = row['keys'][1]
                clicks = row['clicks']
                impressions = row['impressions']
                
                url_path = full_url.replace("https://shreeshivam.com", "").replace("https://www.shreeshivam.com", "")
                
                # If we haven't seen this URL yet, or if this query has MORE clicks than the stored one, save it
                if url_path not in page_data:
                    page_data[url_path] = {
                        'URL': url_path,
                        'Clicks': clicks,
                        'Impressions': impressions,
                        'CTR': round(row['ctr'] * 100, 2),
                        'Position': round(row['position'], 1),
                        'Top Query (The Lure)': query,
                        'Query Clicks': clicks # Tracking how dominant this query is
                    }
                else:
                    # Add total clicks/impressions for the URL
                    page_data[url_path]['Clicks'] += clicks
                    page_data[url_path]['Impressions'] += impressions
                    
                    # Update Top Query if this new one is stronger
                    if clicks > page_data[url_path]['Query Clicks']:
                        page_data[url_path]['Top Query (The Lure)'] = query
                        page_data[url_path]['Query Clicks'] = clicks

        # Convert our dictionary to a clean list of rows
        rows = [data for data in page_data.values()]
                
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"GSC Error: {e}")
        return pd.DataFrame()

def get_ga4_page_data(days=30):
    """Fetches GA4 data using the local token.json."""
    if not GA4_PROPERTY_ID: 
        return pd.DataFrame()
        
    try:
        creds = get_google_credentials()
        ga4_service = build('analyticsdata', 'v1beta', credentials=creds)
        
        request_body = {
            "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
            "dimensions": [{"name": "pagePath"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "engagementRate"},
                {"name": "conversions"}
            ]
        }
        
        response = ga4_service.properties().runReport(
            property=f"properties/{GA4_PROPERTY_ID}", 
            body=request_body
        ).execute()
        
        rows = []
        if 'rows' in response:
            for row in response['rows']:
                rows.append({
                    'URL': row['dimensionValues'][0]['value'],
                    'Sessions': int(row['metricValues'][0]['value']),
                    'Engagement Rate': round(float(row['metricValues'][1]['value']) * 100, 2),
                    'Conversions': float(row['metricValues'][2]['value'])
                })
                
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"GA4 Error: {e}")
        return pd.DataFrame()

def get_shopify_urls():
    """Fetches Shopify URLs using the auto-refreshing 2026 token manager."""
    try:
        # This will automatically grab a cached token or fetch a new 24h one!
        token, source = get_validated_token()
        
        store_domain = os.getenv("SHOPIFY_STORE")
        store_domain = store_domain if ".myshopify.com" in store_domain else f"{store_domain}.myshopify.com"
        
        endpoint = f"https://{store_domain}/admin/api/2026-01/products.json"
        
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }
        params = {"status": "active", "limit": 250} 
        
        response = requests.get(endpoint, headers=headers, params=params)
        urls = []
        
        if response.status_code == 200:
            products = response.json().get('products', [])
            for product in products:
                urls.append({
                    "URL": f"/products/{product['handle']}",
                    "Source of Truth": "Shopify"
                })
            print(f"✅ Shopify connected using {source} token!")
        else:
            print(f"Shopify API Error {response.status_code}: {response.text}")
                
        return pd.DataFrame(urls)
    except Exception as e:
        print(f"Shopify Fetch Error: {e}")
        return pd.DataFrame()