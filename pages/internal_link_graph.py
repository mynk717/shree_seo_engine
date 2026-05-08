# pages/internal_link_graph.py
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from analysis_engine import calculate_internal_pagerank

def render(master_df, notion_df):
    st.markdown("""
    ## 🕸️ Technical Link Topology
    **Larger circles = Higher PageRank. 🚨 Red Glow = Orphaned.**

    ---
    **Interaction Guide:**
    * Hover over any node to see its URL.
    * Scroll/Drag to zoom and pan.
    * Click any node to drill down into its neighborhood.
    """)

    if master_df.empty:
        st.warning("Awaiting data to generate the internal link graph...")
        return

    try:
        graph_data_json = calculate_internal_pagerank(master_df)
    except Exception as e:
        st.error(f"Could not generate internal link graph: {e}")
        return

    if isinstance(graph_data_json, str):
        try:
            graph_data = json.loads(graph_data_json)
        except Exception:
            graph_data = graph_data_json
    else:
        graph_data = graph_data_json

    if isinstance(graph_data, dict):
        full_nodes = graph_data.get("nodes", [])
        full_links = graph_data.get("links", [])
    else:
        full_nodes = []
        full_links = []

    d3_html = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <style>
        body {{
          margin: 0;
          font-family: Arial, sans-serif;
          background: #0f0f0f;
          color: white;
        }}
        #graph {{
          width: 100%;
          height: 850px;
        }}
        .link {{
          stroke: rgba(255,255,255,0.18);
          stroke-width: 1.2px;
        }}
        .url-label {{
          fill: #fff;
          font-size: 10px;
          pointer-events: none;
        }}
        .healthy-node {{
          stroke: rgba(255,255,255,0.4);
          stroke-width: 1px;
        }}
        .orphan-node {{
          stroke: #ff4d4f;
          stroke-width: 2px;
        }}
      </style>
    </head>
    <body>
      <div id="graph"></div>
      <script>
        const fullNodes = {json.dumps(full_nodes)};
        const fullLinks = {json.dumps(full_links)};

        const width = 1200;
        const height = 800;
        const radiusBuffer = 24;

        const colorMap = {{
          "Product": "#4da8b3",
          "Collection": "#2ecc71",
          "Blog": "#f5a524",
          "Page": "#8b5cf6",
          "Other": "#9ca3af"
        }};

        const svg = d3.select("#graph")
          .append("svg")
          .attr("viewBox", [0, 0, width, height])
          .attr("width", "100%")
          .attr("height", height);

        const container = svg.append("g");

        const zoom = d3.zoom()
          .scaleExtent([0.4, 3])
          .on("zoom", (event) => container.attr("transform", event.transform));

        svg.call(zoom);

        function renderGraph(renderNodes, renderLinks, focusNodeId = null) {{
          container.selectAll("*").remove();

          const simulation = d3.forceSimulation(renderNodes)
            .force("link", d3.forceLink(renderLinks).id(d => d.id).distance(120))
            .force("charge", d3.forceManyBody().strength(-220))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("x", d3.forceX(width / 2).strength(d => d.id === focusNodeId ? 0.4 : 0.05))
            .force("y", d3.forceY(height / 2).strength(d => d.id === focusNodeId ? 0.4 : 0.05));

          const link = container.append("g").selectAll("line")
            .data(renderLinks).enter().append("line")
            .attr("class", "link");

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
            .on("mouseout", (event, d) => {{
              d3.select("#label-" + d.id.replace(/[^a-zA-Z0-9]/g, '-')).style("display", "none");
            }});

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
      </script>
    </body>
    </html>
    """

    components.html(d3_html, height=850)