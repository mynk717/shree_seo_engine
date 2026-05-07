import streamlit as st
import pandas as pd
from datetime import datetime
from functools import reduce
import streamlit.components.v1 as components

# Import our live connectors and the engine
from data_connectors import get_notion_seo_edits, get_gsc_page_data, get_ga4_page_data, get_shopify_urls
from analysis_engine import calculate_internal_pagerank

st.set_page_config(page_title="Shree Shivam SEO Engine", page_icon="📈", layout="wide")

@st.cache_data(ttl=600) 
def load_live_data():
    shopify_data = get_shopify_urls()
    gsc_data = get_gsc_page_data()
    ga4_data = get_ga4_page_data()
    notion_data = get_notion_seo_edits()
    
    if not shopify_data.empty: shopify_data['URL'] = shopify_data['URL'].str.rstrip('/').str.lower()
    if not gsc_data.empty: gsc_data['URL'] = gsc_data['URL'].str.rstrip('/').str.lower()
    if not ga4_data.empty: ga4_data['URL'] = ga4_data['URL'].str.rstrip('/').str.lower()

    dfs_to_merge = [df for df in [shopify_data, gsc_data, ga4_data] if not df.empty]
    
    if dfs_to_merge:
        master_seo_df = reduce(lambda left, right: pd.merge(left, right, on='URL', how='outer'), dfs_to_merge)
        if 'Source of Truth' in master_seo_df.columns:
            master_seo_df['Source of Truth'] = master_seo_df['Source of Truth'].fillna('Unknown')
        master_seo_df = master_seo_df.fillna(0)
        
        if 'Clicks' in master_seo_df.columns: master_seo_df['Clicks'] = master_seo_df['Clicks'].astype(int)
        if 'Sessions' in master_seo_df.columns: master_seo_df['Sessions'] = master_seo_df['Sessions'].astype(int)
        if 'Impressions' in master_seo_df.columns: master_seo_df['Impressions'] = master_seo_df['Impressions'].astype(int)
    else:
        master_seo_df = pd.DataFrame()
        
    return master_seo_df, notion_data

master_df, notion_df = load_live_data()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("⚙️ SEO Engine")
page = st.sidebar.radio("Navigation", [
    "Overview Dashboard", 
    "🚨 Advanced Site Audit", 
    "Internal Link Graph",
    "📅 Weekly Impact Report"  # NEW PAGE ADDED HERE
])

# --- PAGE 1: OVERVIEW DASHBOARD ---
if page == "Overview Dashboard":
    st.title("📈 SEO Command Center")
    st.markdown("Combined Shopify + GSC + GA4 URL-Level Performance")
    
    if not master_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        total_clicks = master_df['Clicks'].sum() if 'Clicks' in master_df.columns else 0
        total_imp = master_df['Impressions'].sum() if 'Impressions' in master_df.columns else 0
        total_sess = master_df['Sessions'].sum() if 'Sessions' in master_df.columns else 0
        
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
            if exclude_zeros and 'Position' in display_df.columns:
                display_df = display_df[display_df['Position'] > 0]
            
            if 'Clicks' in display_df.columns:
                display_df = display_df.sort_values(by="Clicks", ascending=False)
                
            st.dataframe(display_df, width='stretch', height=500)
            
        with tab2:
            st.subheader("SEO Impact Tracker")
            st.markdown("Live Google traffic metrics matched directly to your manual Notion edits.")
            
            if not notion_df.empty and not master_df.empty:
                impact_df = notion_df.copy()
                impact_df['Clean_URL'] = impact_df['Page / URL'].str.replace('https://www.shreeshivam.com', '') \
                                                                .str.replace('https://shreeshivam.com', '') \
                                                                .str.rstrip('/').str.lower()
                
                merged_impact = pd.merge(impact_df, master_df, left_on='Clean_URL', right_on='URL', how='left').fillna(0)
                
                display_cols = ['Date', 'Page / URL', 'Notes / Action']
                if 'Clicks' in merged_impact.columns: display_cols.append('Clicks')
                if 'Impressions' in merged_impact.columns: display_cols.append('Impressions')
                if 'Sessions' in merged_impact.columns: display_cols.append('Sessions')
                if 'Top Query (The Lure)' in merged_impact.columns: display_cols.append('Top Query (The Lure)')
                
                for col in ['Clicks', 'Impressions', 'Sessions']:
                    if col in merged_impact.columns:
                        merged_impact[col] = merged_impact[col].astype(int)
                        
                clean_impact = merged_impact[display_cols].astype(str).replace('0', '-')
                st.dataframe(clean_impact, width='stretch', height=500)
            else:
                st.info("Waiting for both Notion and Master Data to populate...")
    else:
        st.warning("Fetching Data... Please wait or check authentication.")

# --- PAGE 2: ADVANCED SITE AUDIT ---
elif page == "🚨 Advanced Site Audit":
    st.title("🩺 Advanced SEO Auditor")
    st.markdown("Automated SEO triage mapping Technical, On-Page, and UX issues to exact URLs.")

    if not master_df.empty and 'Impressions' in master_df.columns:
        with st.container():
            st.markdown("### 🎛️ Audit Filters")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                silo_filter = st.selectbox("Analyze Specific Content Silo", ["Entire Site", "/products", "/collections", "/blogs", "/offers"])
            with col_f2:
                min_imp_filter = st.number_input("Minimum Impressions Threshold (Ignore micro-data)", value=100, step=100)
        
        audit_df = master_df.copy()
        if silo_filter != "Entire Site":
            audit_df = audit_df[audit_df['URL'].str.contains(silo_filter, na=False)]
            
        total_urls = len(audit_df)

        ghost_df = audit_df[(audit_df['Source of Truth'] == 'Shopify') & (audit_df['Impressions'] == 0)]
        
        cannibal_df = pd.DataFrame()
        if 'Top Query (The Lure)' in audit_df.columns:
            valid_queries = audit_df[(audit_df['Top Query (The Lure)'] != 0) & (audit_df['Top Query (The Lure)'] != '0') & (audit_df['Top Query (The Lure)'].notna())]
            query_counts = valid_queries['Top Query (The Lure)'].value_counts()
            duplicate_queries = query_counts[query_counts > 1].index
            cannibal_df = valid_queries[valid_queries['Top Query (The Lure)'].isin(duplicate_queries)].sort_values('Top Query (The Lure)')

        striking_df = audit_df[(audit_df['Impressions'] >= min_imp_filter) & (audit_df['CTR'] > 0) & (audit_df['CTR'] < 2.0)]
        zombie_df = audit_df[(audit_df['Impressions'] >= min_imp_filter) & ((audit_df['Clicks'] == 0) | audit_df['Clicks'].isna())]

        leaky_df = pd.DataFrame()
        if 'Sessions' in audit_df.columns and 'Engagement Rate' in audit_df.columns:
            leaky_df = audit_df[(audit_df['Sessions'] >= 30) & (audit_df['Engagement Rate'] < 45.0) & (audit_df['Engagement Rate'] > 0)]

        ghost_penalty = (len(ghost_df) / total_urls) * 30 if total_urls > 0 else 0
        cannibal_penalty = (len(cannibal_df) / total_urls) * 20 if total_urls > 0 else 0
        striking_penalty = (len(striking_df) / total_urls) * 25 if total_urls > 0 else 0
        leaky_penalty = (len(leaky_df) / total_urls) * 25 if total_urls > 0 else 0
        
        health_score = max(0, round(100 - (ghost_penalty + cannibal_penalty + striking_penalty + leaky_penalty)))

        st.divider()

        col1, col2 = st.columns([1, 3])
        with col1:
            if health_score >= 80: st.metric("Site Health Score", f"{health_score}/100", "Excellent", delta_color="normal")
            elif health_score >= 50: st.metric("Site Health Score", f"{health_score}/100", "Needs Work", delta_color="off")
            else: st.metric("Site Health Score", f"{health_score}/100", "Critical", delta_color="inverse")
                
        with col2:
            st.markdown(f"**Audit Summary:** Scanned **{total_urls}** URLs in the `{silo_filter}` sector.")
            st.progress(health_score / 100.0)

        st.write("---")
        audit_tab1, audit_tab2, audit_tab3 = st.tabs(["⚙️ Technical SEO", "📝 Content & Meta", "🖱️ UX & Conversions"])

        with audit_tab1:
            st.subheader(f"Ghost Pages ({len(ghost_df)} Issues)")
            if not ghost_df.empty: st.dataframe(ghost_df[['URL', 'Source of Truth', 'Impressions']], width='stretch')
            else: st.success("Perfect indexation! No ghost pages found in this silo.")

        with audit_tab2:
            st.subheader(f"Keyword Cannibalization ({len(cannibal_df)} URLs fighting)")
            if not cannibal_df.empty: st.dataframe(cannibal_df[['Top Query (The Lure)', 'URL', 'Impressions', 'Clicks', 'Position']], width='stretch')
            else: st.success("No keyword cannibalization detected.")
            st.write("---")
            st.subheader(f"Striking Distance ({len(striking_df)} Issues)")
            if not striking_df.empty:
                cols = ['URL', 'Impressions', 'CTR', 'Position']
                if 'Top Query (The Lure)' in striking_df.columns: cols.append('Top Query (The Lure)')
                st.dataframe(striking_df[cols].sort_values('Impressions', ascending=False), width='stretch')
            else: st.success("No Striking Distance issues.")
            st.write("---")
            st.subheader(f"Click Zombies ({len(zombie_df)} Issues)")
            if not zombie_df.empty:
                z_cols = ['URL', 'Impressions', 'Position']
                if 'Top Query (The Lure)' in zombie_df.columns: z_cols.append('Top Query (The Lure)')
                st.dataframe(zombie_df[z_cols].sort_values('Impressions', ascending=False), width='stretch')

        with audit_tab3:
            st.subheader(f"Leaky Buckets ({len(leaky_df)} Issues)")
            if not leaky_df.empty: st.dataframe(leaky_df[['URL', 'Sessions', 'Engagement Rate', 'Conversions']].sort_values('Sessions', ascending=False), width='stretch')
            else: st.success("No severe leaky buckets found.")
            st.write("---")
            st.subheader("Hidden Gems (Conversion Drivers)")
            gem_df = audit_df[(audit_df['Conversions'] > 0) & (audit_df['Position'] > 5.0)] if 'Conversions' in audit_df.columns else pd.DataFrame()
            if not gem_df.empty: st.dataframe(gem_df[['URL', 'Conversions', 'Sessions', 'Position']], width='stretch')
            else: st.info("Awaiting more GA4 conversion data to identify gems.")

    else:
        st.warning("Awaiting full dataset to generate the Advanced Audit...")

# --- PAGE 3: INTERNAL LINK GRAPH ---
elif page == "Internal Link Graph":
    st.markdown("""
    ## 🕸️ Technical Link Topology
    **Larger circles = Higher PageRank. 🚨 Red Glow = Orphaned.**
    ---
    **Interaction Guide:** * **Hover** over any node to see its URL.
    * **Scroll/Drag** to zoom and pan.
    * **Click** any node to drill down into its isolated neighborhood.
    """)
    
    graph_data_json = calculate_internal_pagerank(master_df)
    
    d3_html = f"""
    <!DOCTYPE html>
    <meta charset="utf-8">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
      body {{ background-color: #0e1117; margin: 0; color: white; font-family: sans-serif; overflow: hidden; }}
      .link {{ stroke: #555; stroke-opacity: 0.6; stroke-width: 2px; transition: stroke-opacity 0.3s; }}
      text {{ font-size: 13px; fill: #ddd; pointer-events: none; text-shadow: 1px 1px 2px black; font-weight: bold; }}
      @keyframes pulseAlert {{ 0% {{ filter: drop-shadow(0 0 5px #ff4b4b); }} 50% {{ filter: drop-shadow(0 0 20px #ff4b4b); }} 100% {{ filter: drop-shadow(0 0 5px #ff4b4b); }} }}
      .orphan-node {{ stroke: #ff4b4b; stroke-width: 3px; animation: pulseAlert 1.5s infinite; fill: #8b0000 !important; cursor: pointer; }}
      .healthy-node {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; }}
      #ui-panel {{ position: absolute; top: 15px; left: 15px; background: rgba(30, 30, 30, 0.9); padding: 15px; border-radius: 8px; border: 1px solid #444; box-shadow: 0 4px 15px rgba(0,0,0,0.5); z-index: 10; min-width: 200px; }}
      .ui-title {{ font-weight: bold; margin-bottom: 10px; font-size: 15px; border-bottom: 1px solid #555; padding-bottom: 5px; color: white; }}
      .filter-row {{ display: flex; align-items: center; margin-bottom: 8px; cursor: pointer; font-size: 13px; color: #ccc; }}
      .filter-row input {{ margin-right: 8px; cursor: pointer; }}
      .color-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; border: 1px solid #fff; }}
      .reset-btn {{ margin-top: 15px; width: 100%; padding: 8px; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; transition: background-color 0.3s; }}
      .reset-btn:hover {{ background-color: #2980b9; }}
    </style>
    <body>
    <div id="ui-panel">
        <div class="ui-title">Content Silos</div>
        <label class="filter-row"><input type="checkbox" class="silo-filter" value="Home" checked> <span class="color-dot" style="background:#ffffff;"></span> Home</label>
        <label class="filter-row"><input type="checkbox" class="silo-filter" value="Product/Collection" checked> <span class="color-dot" style="background:#3498db;"></span> Products / Collections</label>
        <label class="filter-row"><input type="checkbox" class="silo-filter" value="Blog" checked> <span class="color-dot" style="background:#2ecc71;"></span> Blogs</label>
        <label class="filter-row"><input type="checkbox" class="silo-filter" value="Offer" checked> <span class="color-dot" style="background:#9b59b6;"></span> Offers</label>
        <button id="reset-global" class="reset-btn">🌍 Reset to Global View</button>
    </div>
    <div id="my_dataviz"></div>
    <script>
      const data = {graph_data_json};
      const fullNodes = data.nodes;
      const fullLinks = data.links;
      const width = window.innerWidth;
      const height = 750;
      const radiusBuffer = 30; 
      const colorMap = {{ "Home": "#ffffff", "Product/Collection": "#3498db", "Blog": "#2ecc71", "Offer": "#9b59b6", "Other": "#e67e22" }};

      const svg = d3.select("#my_dataviz").append("svg").attr("width", width).attr("height", height);
      const zoom = d3.zoom().scaleExtent([0.1, 8]).on("zoom", (event) => {{ container.attr("transform", event.transform); }});
      svg.call(zoom);

      const container = svg.append("g");
      let simulation = null;

      function renderGraph(renderNodes, renderLinks, focusNodeId = null) {{
          container.selectAll("*").remove();
          if (simulation) simulation.stop();

          simulation = d3.forceSimulation(renderNodes)
              .force("link", d3.forceLink(renderLinks).id(d => d.id).distance(150))
              .force("charge", d3.forceManyBody().strength(-300))
              .force("center", d3.forceCenter(width / 2, height / 2))
              .force("collide", d3.forceCollide().radius(d => Math.max(12, d.pagerank * 1.5) + 15));

          if (focusNodeId) {{
              simulation.force("x", d3.forceX(width / 2).strength(d => d.id === focusNodeId ? 0.4 : 0.05))
                        .force("y", d3.forceY(height / 2).strength(d => d.id === focusNodeId ? 0.4 : 0.05));
          }}

          const link = container.append("g").selectAll("line").data(renderLinks).enter().append("line").attr("class", "link");
          
          const node = container.append("g").selectAll("circle")
              .data(renderNodes).enter().append("circle")
              .attr("class", d => d.is_orphan ? "orphan-node" : "healthy-node")
              .attr("r", d => Math.max(12, d.pagerank * 1.5)) 
              .attr("fill", d => colorMap[d.type] || colorMap["Other"])
              .on("click", (event, d) => drillDown(d.id))
              .on("mouseover", (event, d) => {{
                  d3.selectAll(".url-label").style("display", "none"); 
                  d3.select("#label-" + d.id.replace(/[^a-zA-Z0-9]/g, '-')).style("display", "");
              }})
              .on("mouseout", (event, d) => {{ d3.select("#label-" + d.id.replace(/[^a-zA-Z0-9]/g, '-')).style("display", "none"); }});
              
          const labels = container.append("g").selectAll("text")
              .data(renderNodes).enter().append("text")
              .attr("class", "url-label")
              .attr("id", d => "label-" + d.id.replace(/[^a-zA-Z0-9]/g, '-')) 
              .attr("dy", -20)
              .attr("text-anchor", "middle")
              .text(d => d.id)
              .style("display", "none"); 

          simulation.on("tick", () => {{
              link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                  .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
              node.attr("cx", d => d.x = Math.max(radiusBuffer, Math.min(width - radiusBuffer, d.x)))
                  .attr("cy", d => d.y = Math.max(radiusBuffer, Math.min(height - radiusBuffer, d.y)));
              labels.attr("x", d => d.x).attr("y", d => d.y);
          }});

          svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
      }}

      function drillDown(focusNodeId) {{
          const neighborIds = fullLinks.filter(link => {{
              const sourceId = typeof link.source === "object" ? link.source.id : link.source;
              const targetId = typeof link.target === "object" ? link.target.id : link.target;
              return sourceId === focusNodeId || targetId === focusNodeId;
          }}).map(link => {{
              const sourceId = typeof link.source === "object" ? link.source.id : link.source;
              const targetId = typeof link.target === "object" ? link.target.id : link.target;
              return sourceId === focusNodeId ? targetId : sourceId;
          }});
          neighborIds.push(focusNodeId);
          const localNodes = fullNodes.filter(n => neighborIds.includes(n.id));
          const localLinks = fullLinks.filter(link => {{
              const sourceId = typeof link.source === "object" ? link.source.id : link.source;
              const targetId = typeof link.target === "object" ? link.target.id : link.target;
              return neighborIds.includes(sourceId) && neighborIds.includes(targetId);
          }});
          renderGraph(localNodes, localLinks, focusNodeId);
      }}

      renderGraph(fullNodes, fullLinks);

      d3.selectAll(".silo-filter").on("change", function() {{
          const activeSilos = Array.from(document.querySelectorAll(".silo-filter:checked")).map(cb => cb.value);
          container.selectAll("circle").style("display", d => activeSilos.includes(d.type) ? "" : "none");
          container.selectAll("text").style("display", "none"); 
          container.selectAll("line").style("display", d => (activeSilos.includes(d.source.type) && activeSilos.includes(d.target.type)) ? "" : "none");
      }});

      d3.select("#reset-global").on("click", () => renderGraph(fullNodes, fullLinks));
    </script>
    </body>
    """
    components.html(d3_html, height=850)

# --- PAGE 5: WEEKLY IMPACT REPORT ---
elif page == "📅 Weekly Impact Report":
    st.title("📅 Saturday Executive Report")
    st.markdown("Automated sprint review mapping effort logged to actual business impact.")

    # 1. Time & Effort Tracking
    st.subheader("⏱️ Sprint Effort")
    t_col1, t_col2, t_col3 = st.columns([1, 1, 2])
    with t_col1:
        st.metric(label="Hours Logged", value="40 hrs", delta="100% capacity")
    with t_col2:
        st.metric(label="Days Active", value="5 Days")
    with t_col3:
        st.markdown("**Sprint Progress**")
        st.progress(1.0) # Full progress bar for 40 hours

    st.divider()

    # 2. Executive Highlights (The "Supporting Work")
    st.subheader("🎯 Sprint Highlights & Roadblocks")
    h_col1, h_col2, h_col3 = st.columns(3)
    
    with h_col1:
        st.success("**🚀 Engineering & Strategy**\n\nSuccessfully built and deployed the custom **Shree Shivam SEO Engine**. Connected Google Search Console, GA4, Shopify, and Notion databases. Drafted automated strategies for Q2.")
    
    with h_col2:
        st.info("**📝 Content Pipeline**\n\nExecuted ongoing content strategy. Successfully published scheduled blog articles targeting non-branded intent and integrated internal linking to core product silos.")
    
    with h_col3:
        st.warning("**🚧 Automation Status**\n\nAttempted deployment of Codex for large-scale content automation. API limits exceeded. Task is officially on hold until quota resets on **May 9th**.")

    st.divider()

    # 3. The Real-World Impact (Data from Notion Edits)
    st.subheader("📈 The Tangible Impact (From Notion Edits)")
    st.markdown("This calculates the live Google traffic *specifically* for the pages that were manually updated in the Notion SEO Edits database.")

    if not notion_df.empty and not master_df.empty:
        # Match Notion URLs to Master Data to calculate impact
        impact_df = notion_df.copy()
        impact_df['Clean_URL'] = impact_df['Page / URL'].str.replace('https://www.shreeshivam.com', '').str.replace('https://shreeshivam.com', '').str.rstrip('/').str.lower()
        
        merged_impact = pd.merge(impact_df, master_df, left_on='Clean_URL', right_on='URL', how='inner')
        
        if not merged_impact.empty:
            edited_clicks = int(merged_impact['Clicks'].sum()) if 'Clicks' in merged_impact.columns else 0
            edited_impressions = int(merged_impact['Impressions'].sum()) if 'Impressions' in merged_impact.columns else 0
            edited_sessions = int(merged_impact['Sessions'].sum()) if 'Sessions' in merged_impact.columns else 0
            
            i_col1, i_col2, i_col3 = st.columns(3)
            i_col1.metric("Traffic from Edited Pages", f"{edited_clicks:,} Clicks", "Direct Result")
            i_col2.metric("Visibility from Edited Pages", f"{edited_impressions:,} Views", "Direct Result")
            i_col3.metric("Sessions from Edited Pages", f"{edited_sessions:,} Sessions", "Direct Result")
            
            st.write("")
            st.markdown("**Performance Breakdown of Edited URLs:**")
            
            display_cols = ['Page / URL', 'Notes / Action']
            if 'Clicks' in merged_impact.columns: display_cols.append('Clicks')
            if 'Impressions' in merged_impact.columns: display_cols.append('Impressions')
            
            # Format nicely for the report
            report_table = merged_impact[display_cols].copy()
            if 'Clicks' in report_table.columns: report_table['Clicks'] = report_table['Clicks'].astype(int)
            if 'Impressions' in report_table.columns: report_table['Impressions'] = report_table['Impressions'].astype(int)
            
            st.dataframe(report_table.sort_values(by='Clicks', ascending=False) if 'Clicks' in report_table.columns else report_table, width='stretch')
        else:
            st.info("The URLs logged in Notion haven't registered traffic data in Google yet. Give it a few days for the APIs to catch up.")
    else:
        st.warning("Waiting for Notion and Google data to populate to calculate impact.")