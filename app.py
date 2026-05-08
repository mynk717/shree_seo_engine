# app.py
import streamlit as st
import pandas as pd
from functools import reduce

from data_connectors import (
    get_notion_seo_edits,
    get_gsc_page_data,
    get_ga4_page_data,
    get_shopify_urls,
)
from analysis_engine import calculate_internal_pagerank

from pages.overview_dashboard import render as render_overview
from pages.advanced_site_audit import render as render_audit
from pages.keyword_content_lab import render as render_keyword_lab
from pages.internal_link_graph import render as render_link_graph
from pages.weekly_impact_report import render as render_weekly_report

st.set_page_config(page_title="Shree Shivam SEO Engine", page_icon="📈", layout="wide")

BRANDS = st.secrets["brands"]

st.sidebar.title("🏢 Portfolio Management")
selected_brand_name = st.sidebar.selectbox("Select Brand to Audit", list(BRANDS.keys()))

@st.cache_data(ttl=600)
def load_brand_data(brand_name):
    config = BRANDS[brand_name]

    gsc_data = get_gsc_page_data(property_url=config["gsc_domain"])
    ga4_data = get_ga4_page_data(property_id=config["ga4_id"])

    shopify_data = get_shopify_urls()
    notion_data = get_notion_seo_edits()

    if not shopify_data.empty and "URL" in shopify_data.columns:
        shopify_data["URL"] = shopify_data["URL"].astype(str).str.rstrip("/").str.lower()

    if not gsc_data.empty and "URL" in gsc_data.columns:
        gsc_data["URL"] = gsc_data["URL"].astype(str).str.rstrip("/").str.lower()

    if not ga4_data.empty and "URL" in ga4_data.columns:
        ga4_data["URL"] = ga4_data["URL"].astype(str).str.rstrip("/").str.lower()

    dfs_to_merge = [df for df in [shopify_data, gsc_data, ga4_data] if not df.empty]

    if dfs_to_merge:
        master_seo_df = reduce(
            lambda left, right: pd.merge(left, right, on="URL", how="outer"),
            dfs_to_merge,
        )
        master_seo_df = master_seo_df.fillna(0)

        for col in ["Clicks", "Sessions", "Impressions"]:
            if col in master_seo_df.columns:
                master_seo_df[col] = pd.to_numeric(master_seo_df[col], errors="coerce").fillna(0).astype(int)

        if "Source of Truth" not in master_seo_df.columns:
            master_seo_df["Source of Truth"] = "Unknown"
    else:
        master_seo_df = pd.DataFrame()

    return master_seo_df, notion_data

master_df, notion_df = load_brand_data(selected_brand_name)
st.sidebar.divider()
st.sidebar.caption("DEBUG")
st.write("Selected brand:", selected_brand_name)
st.write("Master rows:", len(master_df))
st.write("Notion rows:", len(notion_df))
st.write("Notion columns:", list(notion_df.columns) if not notion_df.empty else [])
if not notion_df.empty:
    st.write("Notion sample:")
    st.dataframe(notion_df.head(10), width="stretch")
if not master_df.empty and "URL" in master_df.columns:
    st.write("Master URL sample:")
    st.write(master_df["URL"].head(20).tolist())

st.sidebar.divider()
st.sidebar.title("⚙️ SEO Engine")
page = st.sidebar.radio(
    "Navigation",
    [
        "Overview Dashboard",
        "🚨 Advanced Site Audit",
        "🔬 Keyword & Content Lab",
        "Internal Link Graph",
        "📅 Weekly Impact Report",
    ],
)

if page == "Overview Dashboard":
    render_overview(master_df, notion_df)
elif page == "🚨 Advanced Site Audit":
    render_audit(master_df, notion_df)
elif page == "🔬 Keyword & Content Lab":
    render_keyword_lab(master_df, notion_df)
elif page == "Internal Link Graph":
    render_link_graph(master_df, notion_df)
elif page == "📅 Weekly Impact Report":
    render_weekly_report(master_df, notion_df)