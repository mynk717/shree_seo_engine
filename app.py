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
    "🚨 Site Health Audit", 
    "Action Matrix (Treasure Map)", 
    "Internal Link Graph"
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

# --- PAGE 2: SITE HEALTH AUDIT (THE AUDITOR) ---
elif page == "🚨 Site Health Audit":
    st.title("🩺 Sitebulb-Style Health Audit")
    st.markdown("Automated SEO triage. The engine analyzes your Master Data to calculate a live health score and flags critical architectural issues.")

    if not master_df.empty and 'Impressions' in master_df.columns:
        # --- THE AUDIT ALGORITHM ---
        total_urls = len(master_df)
        
        # 1. Critical: Ghost Products (In Shopify, 0 Impressions)
        ghost_df = master_df[(master_df['Source of Truth'] == 'Shopify') & (master_df['Impressions'] == 0)]
        ghost_count = len(ghost_df)
        
        # 2. Warning: Striking Distance (High Imp, Low CTR)
        striking_df = master_df[(master_df['Impressions'] > 500) & (master_df['CTR'] < 2.0)]
        striking_count = len(striking_df)
        
        # 3. Warning: Leaky Buckets (High Traffic, Low Engagement)
        if 'Sessions' in master_df.columns:
            leaky_df = master_df[(master_df['Sessions'] > 50) & (master_df['Engagement Rate'] < 45.0)]
            leaky_count = len(leaky_df)
        else:
            leaky_df = pd.DataFrame()
            leaky_count = 0

        # Health Math: 100 points minus penalties based on percentage of site affected
        ghost_penalty = (ghost_count / total_urls) * 50 if total_urls > 0 else 0
        leaky_penalty = (leaky_count / total_urls) * 30 if total_urls > 0 else 0
        striking_penalty = (striking_count / total_urls) * 20 if total_urls > 0 else 0
        
        health_score = max(0, round(100 - (ghost_penalty + leaky_penalty + striking_penalty)))

        # --- SCORECARD DISPLAY ---
        col1, col2 = st.columns([1, 3])
        with col1:
            # Color-coded metric based on score
            if health_score >= 80:
                st.metric("Site Health Score", f"{health_score}/100", "Excellent", delta_color="normal")
            elif health_score >= 50:
                st.metric("Site Health Score", f"{health_score}/100", "-Needs Work", delta_color="off")
            else:
                st.metric("Site Health Score", f"{health_score}/100", "Critical", delta_color="inverse")
                
        with col2:
            st.markdown(f"**Audit Summary:** Scanned **{total_urls}** URLs. Found **{ghost_count}** critical errors and **{leaky_count + striking_count}** optimization warnings.")
            st.progress(health_score / 100.0)

        st.divider()

        # --- CRITICAL FIXES ---
        st.error(f"🛑 CRITICAL ERRORS ({ghost_count} Issues)")
        with st.expander("View Ghost Products (Orphaned / Not Indexed)"):
            st.markdown("**Issue:** These URLs exist in your Shopify backend but are receiving 0 impressions from Google. They are likely orphaned or blocked.")
            if not ghost_df.empty:
                st.dataframe(ghost_df[['URL', 'Source of Truth', 'Impressions', 'Clicks']], width='stretch')
            else:
                st.success("No Ghost Products found! Your inventory is perfectly indexed.")

        # --- WARNINGS ---
        st.warning(f"⚠️ WARNINGS ({striking_count + leaky_count} Issues)")
        with st.expander(f"View Striking Distance Pages ({striking_count})"):
            st.markdown("**Issue:** High visibility (Google likes them), but users aren't clicking (Bad Meta Titles). Needs immediate text optimization.")
            if not striking_df.empty:
                cols = ['URL', 'Impressions', 'CTR', 'Position']
                if 'Top Query (The Lure)' in striking_df.columns: cols.append('Top Query (The Lure)')
                st.dataframe(striking_df[cols].sort_values('Impressions', ascending=False), width='stretch')
            else:
                st.success("No Striking Distance issues.")

        with st.expander(f"View Leaky Buckets ({leaky_count})"):
            st.markdown("**Issue:** Users are landing on these pages but leaving immediately (<45% Engagement). Needs better internal linking or UX.")
            if not leaky_df.empty:
                st.dataframe(leaky_df[['URL', 'Sessions', 'Engagement Rate', 'Conversions']].sort_values('Sessions', ascending=False), width='stretch')
            else:
                st.success("No Leaky Buckets found.")

        # --- NOTICES ---
        st.info("💡 NOTICES (Opportunities)")
        with st.expander("View Hidden Gems"):
            gem_df = master_df[(master_df['Conversions'] > 0) & (master_df['Position'] > 5.0)] if 'Conversions' in master_df.columns else pd.DataFrame()
            st.markdown("**Opportunity:** These pages actually generate conversions, but rank poorly. Pass PageRank to these URLs to scale revenue.")
            if not gem_df.empty:
                st.dataframe(gem_df[['URL', 'Conversions', 'Sessions', 'Position']], width='stretch')
            else:
                st.write("Need more conversion data to identify Hidden Gems.")

    else:
        st.warning("Awaiting full dataset to generate the Health Audit...")

# --- PAGE 3: ACTION MATRIX (TREASURE MAP) ---
# --- PAGE 2: ACTION MATRIX (TREASURE MAP) ---
elif page == "Action Matrix (Treasure Map)":
    st.title("🗺️ SEO Treasure Map")
    st.markdown("Automated algorithmic insights based on combined metrics.")

    if not master_df.empty and 'Impressions' in master_df.columns and 'Sessions' in master_df.columns:
        min_impressions = 500
        poor_ctr = 2.0
        min_sessions = 50
        poor_engagement = 45.0

        st.divider()

        # 1. Striking Distance
        st.subheader("🎯 Striking Distance (Needs Title/Meta Optimization)")
        st.info(f"High visibility (>{min_impressions} Imp), but low clicks (<{poor_ctr}% CTR).")
        striking_df = master_df[(master_df['Impressions'] > min_impressions) & (master_df['CTR'] < poor_ctr)]
        striking_df = striking_df.sort_values(by='Impressions', ascending=False)
        st.dataframe(striking_df[['URL', 'Impressions', 'CTR', 'Position']], width='stretch')

        st.divider()

        # 2. Leaky Buckets
        st.subheader("🪣 Leaky Buckets (Needs CRO & Content Updates)")
        st.info(f"High traffic (>{min_sessions} Sessions), but users are bouncing (<{poor_engagement}% Engagement).")
        leaky_df = master_df[(master_df['Sessions'] > min_sessions) & (master_df['Engagement Rate'] < poor_engagement)]
        leaky_df = leaky_df.sort_values(by='Sessions', ascending=False)
        st.dataframe(leaky_df[['URL', 'Sessions', 'Engagement Rate', 'Conversions']], width='stretch')

        st.divider()

        # 3. Hidden Gems
        st.subheader("💎 Hidden Gems (Needs Internal Link Injections)")
        st.info("These pages generate conversions but rank poorly. Boost them with internal links!")
        gem_df = master_df[(master_df['Conversions'] > 0) & (master_df['Position'] > 5.0)]
        gem_df = gem_df.sort_values(by='Conversions', ascending=False)
        st.dataframe(gem_df[['URL', 'Conversions', 'Sessions', 'Position', 'Clicks']], width='stretch')

        st.divider()

        # 4. Ghost Products (The Indexation Gap)
        st.subheader("👻 Ghost Products (The Indexation Gap)")
        st.info("These products exist in Shopify and can be purchased, but Google Search Console shows 0 impressions. They are completely invisible to organic search!")
        
        if 'Source of Truth' in master_df.columns:
            ghost_df = master_df[(master_df['Source of Truth'] == 'Shopify') & (master_df['Impressions'] == 0)]
            st.dataframe(ghost_df[['URL', 'Source of Truth', 'Impressions', 'Clicks']], width='stretch')
        else:
            st.warning("Shopify data missing. Ensure your Shopify token is correct.")

    else:
        st.warning("Awaiting full dataset to generate insights...")

# --- PAGE 4: INTERNAL LINK GRAPH ---
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