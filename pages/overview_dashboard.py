import streamlit as st
import pandas as pd

def render(master_df, notion_df):
    st.title("📈 SEO Command Center")
    st.markdown("Combined Shopify + GSC + GA4 URL-Level Performance")

    if not master_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        total_clicks = master_df["Clicks"].sum() if "Clicks" in master_df.columns else 0
        total_imp = master_df["Impressions"].sum() if "Impressions" in master_df.columns else 0
        total_sess = master_df["Sessions"].sum() if "Sessions" in master_df.columns else 0

        col1.metric("Total Clicks (30d)", f"{total_clicks:,}")
        col2.metric("Total Impressions (30d)", f"{total_imp:,}")
        col3.metric("Total Sessions (30d)", f"{total_sess:,}")
        col4.metric("SEO Edits Logged", f"{len(notion_df)}")

        st.divider()

        tab1, tab2 = st.tabs(["URL Performance Matrix", "🚀 SEO Impact Tracker"])

        with tab1:
            st.subheader("The Master Data Table")
            exclude_zeros = st.checkbox("Hide Unranked Pages (Position 0)", value=True)

            display_df = master_df.copy()
            if exclude_zeros and "Position" in display_df.columns:
                display_df = display_df[display_df["Position"] > 0]

            if "Clicks" in display_df.columns:
                display_df = display_df.sort_values(by="Clicks", ascending=False)

            st.dataframe(display_df, width="stretch", height=500)

        with tab2:
            st.subheader("SEO Impact Tracker")
            st.markdown("Live Google traffic metrics matched directly to your manual Notion edits.")

            if not notion_df.empty and not master_df.empty:
                impact_df = notion_df.copy()
                impact_df["Clean_URL"] = (
                    impact_df["Page / URL"]
                    .str.replace("https://www.shreeshivam.com", "", regex=False)
                    .str.replace("https://shreeshivam.com", "", regex=False)
                    .str.rstrip("/")
                    .str.lower()
                )

                merged_impact = pd.merge(
                    impact_df,
                    master_df,
                    left_on="Clean_URL",
                    right_on="URL",
                    how="left",
                ).fillna(0)

                display_cols = ["Date", "Page / URL", "Notes / Action"]
                if "Clicks" in merged_impact.columns:
                    display_cols.append("Clicks")
                if "Impressions" in merged_impact.columns:
                    display_cols.append("Impressions")
                if "Sessions" in merged_impact.columns:
                    display_cols.append("Sessions")
                if "Top Query (The Lure)" in merged_impact.columns:
                    display_cols.append("Top Query (The Lure)")

                for col in ["Clicks", "Impressions", "Sessions"]:
                    if col in merged_impact.columns:
                        merged_impact[col] = merged_impact[col].astype(int)

                clean_impact = merged_impact[display_cols].astype(str).replace("0", "-")
                st.dataframe(clean_impact, width="stretch", height=500)
            else:
                st.info("Waiting for both Notion and Master Data to populate...")
    else:
        st.warning("Fetching Data... Please wait or check authentication.")