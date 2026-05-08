# pages/keyword_content_lab.py
import streamlit as st
import pandas as pd

def render(master_df, notion_df):
    st.title("🔬 Keyword & Content Lab")
    st.markdown("Deep dive into exact search queries, content performance, and semantic gaps.")

    if not master_df.empty and "Top Query (The Lure)" in master_df.columns:
        tab_kw, tab_content = st.tabs(["🔑 The Keyword Matrix", "📄 Content Inspector (URL DNA)"])

        with tab_kw:
            st.subheader("Aggregate Keyword Performance")
            st.markdown(
                "This views your site from the perspective of the **Search Query**, not the URL. "
                "Find high-volume keywords and spot cannibalization."
            )

            valid_queries = master_df[
                (master_df["Top Query (The Lure)"] != 0) &
                (master_df["Top Query (The Lure)"] != "0") &
                (master_df["Top Query (The Lure)"].notna())
            ]

            if not valid_queries.empty:
                kw_df = (
                    valid_queries.groupby("Top Query (The Lure)")
                    .agg({
                        "Clicks": "sum",
                        "Impressions": "sum",
                        "URL": "count",
                    })
                    .rename(columns={"URL": "Pages Ranking"})
                    .reset_index()
                )

                kw_df["Aggregate CTR (%)"] = (
                    (kw_df["Clicks"] / kw_df["Impressions"]) * 100
                ).round(2)
                kw_df = kw_df.sort_values("Impressions", ascending=False)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Unique Keywords Won", len(kw_df))
                col2.metric(
                    "Highest Volume Query",
                    kw_df.iloc[0]["Top Query (The Lure)"] if not kw_df.empty else "N/A",
                )
                col3.metric("Queries > 1000 Imp", len(kw_df[kw_df["Impressions"] > 1000]))
                col4.metric("Cannibalized Queries", len(kw_df[kw_df["Pages Ranking"] > 1]))

                st.dataframe(kw_df, width="stretch", height=500)
            else:
                st.info("No valid keyword rows found yet.")

        with tab_content:
            st.subheader("Single URL Inspector")
            st.markdown("Select any URL to see its complete Google Search Console and GA4 DNA.")

            if "URL" in master_df.columns:
                url_list = master_df["URL"].dropna().unique().tolist()
                url_list.sort()
            else:
                url_list = []

            selected_url = st.selectbox("Search or Select a URL to Inspect", url_list)

            if selected_url:
                url_data = master_df[master_df["URL"] == selected_url].iloc[0]

                st.markdown(f"### Target: `{selected_url}`")

                st.markdown("#### 🔍 Search Visibility (GSC)")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Top Query (The Lure)", url_data.get("Top Query (The Lure)", "N/A"))
                c2.metric("Clicks", int(url_data.get("Clicks", 0)))
                c3.metric("Impressions", int(url_data.get("Impressions", 0)))
                c4.metric("Avg Position", round(url_data.get("Position", 0), 1))

                st.markdown("#### 🖱️ User Behavior (GA4)")
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Sessions", int(url_data.get("Sessions", 0)))
                c6.metric("Engagement Rate", f"{url_data.get('Engagement Rate', 0)}%")
                c7.metric("Conversions", int(url_data.get("Conversions", 0)))
                c8.metric(
                    "Bounce Rate",
                    f"{round(100 - float(url_data.get('Engagement Rate', 0)), 1)}%"
                    if url_data.get("Engagement Rate")
                    else "N/A",
                )

                if not notion_df.empty and "Page / URL" in notion_df.columns:
                    clean_selected = (
                        selected_url
                        .replace("https://www.shreeshivam.com", "")
                        .replace("https://shreeshivam.com", "")
                        .rstrip("/")
                        .lower()
                    )

                    notion_df_temp = notion_df.copy()
                    notion_df_temp["Clean_URL"] = (
                        notion_df_temp["Page / URL"]
                        .str.replace("https://www.shreeshivam.com", "", regex=False)
                        .str.replace("https://shreeshivam.com", "", regex=False)
                        .str.rstrip("/")
                        .str.lower()
                    )

                    edit_history = notion_df_temp[notion_df_temp["Clean_URL"] == clean_selected]

                    if not edit_history.empty:
                        st.info("📝 **Notion Edit History Found for this URL:**")
                        st.dataframe(edit_history[["Date", "Notes / Action"]], width="stretch")
                    else:
                        st.write("No manual SEO edits logged in Notion for this URL yet.")
    else:
        st.warning("Awaiting keyword data from Google Search Console...")