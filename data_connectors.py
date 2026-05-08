import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from shopify_token_manager import get_validated_token
import streamlit as st

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
GSC_PROPERTY = os.getenv("GSC_PROPERTY", "sc-domain:shreeshivam.com")
# Combined Scopes for both GSC and GA4
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/analytics.readonly'
]

def get_google_credentials():
    """Authenticates using Streamlit Secrets (Cloud) or token.json (Local)."""
    
    # 1. Try Cloud Secrets First (The Bypass)
    try:
        if "google_oauth" in st.secrets:
            oauth_secrets = st.secrets["google_oauth"]
            creds = Credentials(
                token=None,  # We leave this blank so it forces a refresh
                refresh_token=oauth_secrets["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=oauth_secrets["client_id"],
                client_secret=oauth_secrets["client_secret"],
                scopes=SCOPES
            )
            return creds
    except Exception as e:
        print(f"Cloud Auth failed, falling back to local: {e}")

    # 2. Fallback to Local Desktop Testing
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        return creds
        
    print("CRITICAL: No Google credentials found in secrets or locally.")
    return None

def get_notion_seo_edits():
    notion_token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DB_SEO_EDITS", "34ccbec2-7659-81e3-978c-dfd1d247a437")

    if not notion_token or not db_id:
        print("Missing Notion credentials for Edits DB.")
        return pd.DataFrame()

    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    rows = []
    payload = {"page_size": 100}
    next_cursor = None

    try:
        while True:
            if next_cursor:
                payload["start_cursor"] = next_cursor

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                print(f"Notion Fetch Error: {response.text}")
                return pd.DataFrame()

            data = response.json()
            for page in data.get("results", []):
                props = page.get("properties", {})

                title_arr = props.get("Page / URL", {}).get("title", [])
                page_url = "".join(x.get("plain_text", "") for x in title_arr).strip()

                date_obj = props.get("Changed On", {}).get("date", {})
                changed_on = date_obj.get("start")

                status_obj = props.get("Status", {}).get("select", {})
                status = status_obj.get("name", "") if status_obj else ""

                change_type_obj = props.get("Change Type", {}).get("select", {})
                change_type = change_type_obj.get("name", "") if change_type_obj else ""

                after_arr = props.get("After", {}).get("rich_text", [])
                after_text = "".join(x.get("plain_text", "") for x in after_arr).strip()

                notes_arr = props.get("Notes", {}).get("rich_text", [])
                notes = "".join(x.get("plain_text", "") for x in notes_arr).strip()

                before_arr = props.get("Before", {}).get("rich_text", [])
                before_text = "".join(x.get("plain_text", "") for x in before_arr).strip()

                rows.append({
                    "Date": changed_on,
                    "Status": status,
                    "Change Type": change_type,
                    "Page / URL": page_url,
                    "Notes / Action": after_text or notes or before_text,
                })

            if not data.get("has_more"):
                break
            next_cursor = data.get("next_cursor")

        return pd.DataFrame(rows)

    except Exception as e:
        print(f"Failed to fetch Notion Edits: {e}")
        return pd.DataFrame()

def get_gsc_page_data(property_url=None, days=30):
    """Fetches GSC data for a specific property URL."""
    # Fallback to default if no brand is passed
    target_property = property_url if property_url else os.getenv("GSC_PROPERTY", "sc-domain:shreeshivam.com")
    
    try:
        creds = get_google_credentials()
        service = build('searchconsole', 'v1', credentials=creds)
        
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['page', 'query'],
            'rowLimit': 10000 
        }
        
        response = service.searchanalytics().query(siteUrl=target_property, body=request).execute()
        
        page_data = {}
        if 'rows' in response:
            for row in response['rows']:
                full_url = row['keys'][0]
                query = row['keys'][1]
                clicks = row['clicks']
                impressions = row['impressions']
                
                # --- UPDATED URL CLEANING (Surgical Fix) ---
                clean_url = full_url.replace("https://", "").replace("http://", "").replace("www.", "")
                
                # Dynamically determine the domain to remove based on the brand being fetched
                domain_to_remove = target_property.replace("sc-domain:", "").replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
                
                # Extract the path (e.g., /products/saree)
                url_path = "/" + clean_url.replace(domain_to_remove, "").lstrip("/")
                
                if url_path not in page_data:
                    page_data[url_path] = {
                        'URL': url_path,
                        'Clicks': clicks,
                        'Impressions': impressions,
                        'CTR': round(row['ctr'] * 100, 2),
                        'Position': round(row['position'], 1),
                        'Top Query (The Lure)': query,
                        'Query Clicks': clicks
                    }
                else:
                    page_data[url_path]['Clicks'] += clicks
                    page_data[url_path]['Impressions'] += impressions
                    if clicks > page_data[url_path]['Query Clicks']:
                        page_data[url_path]['Top Query (The Lure)'] = query
                        page_data[url_path]['Query Clicks'] = clicks

        return pd.DataFrame(list(page_data.values()))
    except Exception as e:
        print(f"GSC Error for {target_property}: {e}")
        return pd.DataFrame()

def get_ga4_page_data(property_id=None, days=30):
    """Fetches GA4 data for a specific property ID."""
    target_id = property_id if property_id else os.getenv("GA4_PROPERTY_ID")
    
    if not target_id: 
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
            property=f"properties/{target_id}", 
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
        print(f"GA4 Error for ID {target_id}: {e}")
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