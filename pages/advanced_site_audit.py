# pages/advanced_site_audit.py
import streamlit as st
import pandas as pd

def render(master_df, notion_df):
    st.title("🩺 Advanced SEO Auditor")
    st.markdown("Automated SEO triage mapping Technical, On-Page, and UX issues to exact URLs.")

    if not master_df.empty and "Impressions" in master_df.columns:
        with st.container():
            st.markdown("### 🎛️ Audit Filters")
            col_f1, col_f2 = st.columns(2)

            with col_f1:
                silo_filter = st.selectbox(
                    "Analyze Specific Content Silo",
                    ["Entire Site", "/products", "/collections", "/blogs", "/offers"],
                )

            with col_f2:
                min_imp_filter = st.number_input(
                    "Minimum Impressions Threshold (Ignore micro-data)",
                    value=100,
                    step=100,
                )

        audit_df = master_df.copy()
        if silo_filter != "Entire Site":
            audit_df = audit_df[audit_df["URL"].str.contains(silo_filter, na=False)]

        total_urls = len(audit_df)

        ghost_df = pd.DataFrame()
        if "Source of Truth" in audit_df.columns and "Impressions" in audit_df.columns:
            ghost_df = audit_df[
                (audit_df["Source of Truth"] == "Shopify") &
                (audit_df["Impressions"] == 0)
            ]

        cannibal_df = pd.DataFrame()
        if "Top Query (The Lure)" in audit_df.columns:
            valid_queries = audit_df[
                (audit_df["Top Query (The Lure)"] != 0) &
                (audit_df["Top Query (The Lure)"] != "0") &
                (audit_df["Top Query (The Lure)"].notna())
            ]
            if not valid_queries.empty:
                query_counts = valid_queries["Top Query (The Lure)"].value_counts()
                duplicate_queries = query_counts[query_counts > 1].index
                cannibal_df = valid_queries[
                    valid_queries["Top Query (The Lure)"].isin(duplicate_queries)
                ].sort_values("Top Query (The Lure)")

        striking_df = audit_df[
            (audit_df["Impressions"] >= min_imp_filter) &
            (audit_df["CTR"] > 0) &
            (audit_df["CTR"] < 2.0)
        ] if "CTR" in audit_df.columns else pd.DataFrame()

        zombie_df = audit_df[
            (audit_df["Impressions"] >= min_imp_filter) &
            ((audit_df["Clicks"] == 0) | audit_df["Clicks"].isna())
        ] if "Clicks" in audit_df.columns else pd.DataFrame()

        leaky_df = pd.DataFrame()
        if "Sessions" in audit_df.columns and "Engagement Rate" in audit_df.columns:
            leaky_df = audit_df[
                (audit_df["Sessions"] >= 30) &
                (audit_df["Engagement Rate"] < 45.0) &
                (audit_df["Engagement Rate"] > 0)
            ]

        ghost_penalty = (len(ghost_df) / total_urls) * 30 if total_urls > 0 else 0
        cannibal_penalty = (len(cannibal_df) / total_urls) * 20 if total_urls > 0 else 0
        striking_penalty = (len(striking_df) / total_urls) * 25 if total_urls > 0 else 0
        leaky_penalty = (len(leaky_df) / total_urls) * 25 if total_urls > 0 else 0
        health_score = max(0, round(100 - (ghost_penalty + cannibal_penalty + striking_penalty + leaky_penalty)))

        st.divider()

        col1, col2 = st.columns([1, 3])
        with col1:
            if health_score >= 80:
                st.metric("Site Health Score", f"{health_score}/100", "Excellent", delta_color="normal")
            elif health_score >= 50:
                st.metric("Site Health Score", f"{health_score}/100", "Needs Work", delta_color="off")
            else:
                st.metric("Site Health Score", f"{health_score}/100", "Critical", delta_color="inverse")

        with col2:
            st.markdown(f"**Audit Summary:** Scanned **{total_urls}** URLs in the `{silo_filter}` sector.")
            st.progress(health_score / 100.0)

        st.write("---")
        audit_tab1, audit_tab2, audit_tab3 = st.tabs(["⚙️ Technical SEO", "📝 Content & Meta", "🖱️ UX & Conversions"])

        with audit_tab1:
            st.subheader(f"Ghost Pages ({len(ghost_df)} Issues)")
            if not ghost_df.empty:
                st.dataframe(ghost_df[["URL", "Source of Truth", "Impressions"]], width="stretch")
            else:
                st.success("Perfect indexation! No ghost pages found in this silo.")

        with audit_tab2:
            st.subheader(f"Keyword Cannibalization ({len(cannibal_df)} URLs fighting)")
            if not cannibal_df.empty:
                st.dataframe(cannibal_df[["Top Query (The Lure)", "URL", "Impressions", "Clicks", "Position"]], width="stretch")
            else:
                st.success("No keyword cannibalization detected.")

            st.write("---")
            st.subheader(f"Striking Distance ({len(striking_df)} Issues)")
            if not striking_df.empty:
                cols = ["URL", "Impressions", "CTR", "Position"]
                if "Top Query (The Lure)" in striking_df.columns:
                    cols.append("Top Query (The Lure)")
                st.dataframe(striking_df[cols].sort_values("Impressions", ascending=False), width="stretch")
            else:
                st.success("No Striking Distance issues.")

            st.write("---")
            st.subheader(f"Click Zombies ({len(zombie_df)} Issues)")
            if not zombie_df.empty:
                z_cols = ["URL", "Impressions", "Position"]
                if "Top Query (The Lure)" in zombie_df.columns:
                    z_cols.append("Top Query (The Lure)")
                st.dataframe(zombie_df[z_cols].sort_values("Impressions", ascending=False), width="stretch")
            else:
                st.success("No click zombie issues.")

        with audit_tab3:
            st.subheader(f"Leaky Buckets ({len(leaky_df)} Issues)")
            if not leaky_df.empty:
                st.dataframe(
                    leaky_df[["URL", "Sessions", "Engagement Rate", "Conversions"]].sort_values("Sessions", ascending=False),
                    width="stretch",
                )
            else:
                st.success("No severe leaky buckets found.")

            st.write("---")
            st.subheader("Hidden Gems (Conversion Drivers)")
            gem_df = audit_df[
                (audit_df["Conversions"] > 0) & (audit_df["Position"] > 5.0)
            ] if "Conversions" in audit_df.columns and "Position" in audit_df.columns else pd.DataFrame()

            if not gem_df.empty:
                st.dataframe(gem_df[["URL", "Conversions", "Sessions", "Position"]], width="stretch")
            else:
                st.info("Awaiting more GA4 conversion data to identify gems.")
    else:
        st.warning("Awaiting full dataset to generate the Advanced Audit...")