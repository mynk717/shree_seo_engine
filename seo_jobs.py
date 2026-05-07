import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Google & Notion Auth
import google.auth
from google.auth.transport.requests import Request
from notion_client import Client

# 1. Unified Configuration & Auth
load_dotenv(r"C:\Users\shree\OneDrive\Documents\mynk\Credentials\apikeys.env.txt")

class SEOEngine:
    def __init__(self):
        # API Keys
        self.notion_token = os.getenv("NOTION_TOKEN")
        self.gsc_property = os.getenv("GSC_PROPERTY").strip('"')
        self.ga4_property = os.getenv("GA4_PROPERTY_ID")
        
        # Notion DBs
        self.db_edits = os.getenv("NOTION_DB_SEO_EDITS", "34ccbec2-7659-81e3-978c-dfd1d247a437")
        self.db_metrics = os.getenv("NOTION_DB_METRICS")
        self.db_pages = os.getenv("NOTION_DB_PAGES")
        
        # Clients
        self.notion = Client(auth=self.notion_token, notion_version="2022-06-28")
        self.google_creds = self._get_google_adc()

    def _get_google_adc(self):
        """Unified Google ADC Authentication."""
        scopes = [
            "https://www.googleapis.com/auth/webmasters",
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/content"
        ]
        creds, _ = google.auth.default(scopes=scopes)
        if not creds.valid:
            creds.refresh(Request())
        return creds

    # -----------------------------------------
    # CORE METHOD 1: The Indexing Checker
    # -----------------------------------------
    def check_url_indexing(self, url):
        """Uses official GSC Inspection API to check if a URL is indexed."""
        endpoint = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
        payload = {"inspectionUrl": url, "siteUrl": self.gsc_property}
        headers = {"Authorization": f"Bearer {self.google_creds.token}"}
        
        res = requests.post(endpoint, json=payload, headers=headers)
        status = res.json().get('inspectionResult', {}).get('indexStatusResult', {}).get('verdict', 'UNKNOWN')
        return status == "PASS"

    def fetch_non_branded_queries(self, page_url):
        """Fetches high-value queries, excluding branded 'shree/shivam' terms."""
        endpoint = f"https://www.googleapis.com/webmasters/v3/sites/{self.gsc_property.replace(':', '%3A')}/searchAnalytics/query"
        payload = {
            "startDate": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "endDate": datetime.now().strftime("%Y-%m-%d"),
            "dimensions": ["query"],
            "dimensionFilterGroups": [{
                "filters": [
                    {"dimension": "page", "operator": "equals", "expression": page_url},
                    {"dimension": "query", "operator": "notContains", "expression": "shree"},
                    {"dimension": "query", "operator": "notContains", "expression": "shivam"}
                ]
            }],
            "rowLimit": 5
        }
        res = requests.post(endpoint, json=payload, headers={"Authorization": f"Bearer {self.google_creds.token}"})
        rows = res.json().get('rows', [])
        return [r['keys'][0] for r in rows]

    # -----------------------------------------
    # CORE METHOD 2: Notion Loggers
    # -----------------------------------------
    def log_manual_edit(self, url, notes, status_name="Published", change_type="Blog Published", gsc_submitted=True):
        """Logs manual SEO work directly to the Edits database with the correct schema."""
        try:
            self.notion.pages.create(
                parent={"database_id": self.db_edits},
                properties={
                    "Page / URL": {
                        "title": [{"text": {"content": url}}]
                    },
                    "Notes": {
                        "rich_text": [{"text": {"content": notes}}]
                    },
                    "Status": {
                        "select": {"name": status_name}
                    },
                    "Change Type": {
                        "select": {"name": change_type}
                    },
                    "Changed On": {
                        "date": {"start": datetime.now().strftime("%Y-%m-%d")}
                    },
                    "GSC Submitted": {
                        "checkbox": gsc_submitted
                    }
                }
            )
            print(f"✅ Logged to Notion Edits: {url}")
        except Exception as e:
            print(f"❌ Failed to log to Notion. Error: {e}")

    def log_indexing_status(self, page_name, indexed, queries):
        """Pushes indexing status and discovered queries to the Metrics Dashboard."""
        status_text = "Indexed ✅" if indexed else "Pending ⏳"
        query_text = ", ".join(queries) if queries else "No non-branded queries yet"
        
        self.notion.pages.create(
            parent={"database_id": self.db_metrics},
            properties={
                "Metric": {"title": [{"text": {"content": page_name}}]},
                "Value": {"rich_text": [{"text": {"content": status_text}}]},
                "Unit": {"rich_text": [{"text": {"content": "Status"}}]},
                "Notes": {"rich_text": [{"text": {"content": f"New Queries: {query_text}"}}]}
            }
        )
        print(f"✅ Logged to Notion Metrics: {page_name} | {status_text}")

# ==========================================
# EXECUTION WORKFLOWS
# ==========================================
if __name__ == "__main__":
    engine = SEOEngine()
    
    print("\n🚀 Starting Daily SEO Operations...")

   # Task 2: Log any new manual actions
   # Log the new Bridal Saree Guide
    engine.log_manual_edit(
        url="https://www.shreeshivam.com/blogs/blog/wedding-saree-for-bride-the-ultimate-2026-bridal-saree-guide",
        notes="Published ultimate 2026 bridal saree guide. Targeted commercial/informational intent for wedding sarees. Added internal links to main Saree collections.",
        status_name="Published",
        change_type="Blog Published",
        gsc_submitted=True # Since you mentioned you already submitted it for indexation
    )