import pandas as pd
from data_connectors import get_notion_seo_edits, get_gsc_page_data, get_ga4_page_data

def run_impact_report():
    print("🔍 Fetching SEO Edits from Notion...")
    notion_df = get_notion_seo_edits()

    if notion_df.empty:
        print("❌ No edits found in Notion database.")
        return

    print("📊 Fetching GSC & GA4 Performance Data (Last 30 Days)...")
    gsc_df = get_gsc_page_data()
    ga4_df = get_ga4_page_data()

    # 1. Clean Notion URLs so they match Google's format (strip domains and trailing slashes)
    notion_df['Clean_URL'] = notion_df['Page / URL'].str.replace('https://www.shreeshivam.com', '')\
                                                    .str.replace('https://shreeshivam.com', '')\
                                                    .str.rstrip('/').str.lower()
    
    # Clean Google URLs just in case
    if not gsc_df.empty: gsc_df['URL'] = gsc_df['URL'].str.rstrip('/').str.lower()
    if not ga4_df.empty: ga4_df['URL'] = ga4_df['URL'].str.rstrip('/').str.lower()

    # 2. Isolate unique edited URLs
    edited_urls = notion_df[['Clean_URL', 'Date', 'Notes / Action']].drop_duplicates('Clean_URL')

    # 3. Stitch the data together!
    print("🧠 Analyzing Impact...")
    result = edited_urls
    if not gsc_df.empty:
        result = pd.merge(result, gsc_df, left_on='Clean_URL', right_on='URL', how='left')
    if not ga4_df.empty:
        result = pd.merge(result, ga4_df, left_on='Clean_URL', right_on='URL', how='left')

    # Fill NaNs with 0 for clean math
    result = result.fillna(0)

    # 4. Print the Dashboard in Terminal
    print("\n" + "="*85)
    print("📈 SEO EDITS IMPACT REPORT (Last 30 Days of Traffic)")
    print("="*85)

    # Filter out empty URLs
    result = result[result['Clean_URL'] != 0]

    for index, row in result.iterrows():
        # Skip if it couldn't find a matching URL
        if row['Clean_URL'] == "": continue
        
        clicks = int(row.get('Clicks', 0))
        impressions = int(row.get('Impressions', 0))
        sessions = int(row.get('Sessions', 0))
        
        print(f"🔗 URL:      {row['Clean_URL']}")
        print(f"🗓️ Edited:   {row.get('Date', 'Unknown')} | Action: {row.get('Notes / Action', 'N/A')}")
        print(f"🚀 Impact:   {clicks} Clicks | {impressions} Impressions | {sessions} Sessions")
        print("-" * 85)

if __name__ == "__main__":
    run_impact_report()