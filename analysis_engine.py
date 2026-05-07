import networkx as nx
import json
import pandas as pd

def calculate_internal_pagerank(df=None):
    """
    Dynamically builds a site structure graph from the live dataframe, 
    calculates PageRank, and flags true Orphan pages.
    """
    pages = []
    links = []

    if df is None or df.empty:
        # Failsafe mock data just in case the DF is empty
        pages = [{"id": "/", "type": "Home", "traffic": 5000}]
        links = []
    else:
        # 1. Build the Live Nodes
        pages.append({"id": "/", "type": "Home", "traffic": 5000})
        
        for index, row in df.iterrows():
            url = str(row['URL']).strip()
            if url in ['/', '', 'nan']: continue

            # Grab traffic metrics for scaling
            traffic = int(row.get('Sessions', row.get('Clicks', 10)))

            # Auto-Categorize Silos
            if '/blog' in url: page_type = "Blog"
            elif '/products' in url or '/collections' in url: page_type = "Product/Collection"
            elif '/offers' in url: page_type = "Offer"
            else: page_type = "Other"

            pages.append({"id": url, "type": page_type, "traffic": traffic})

            # 2. Auto-Generate Hierarchical Links
            # This links a URL to its parent folder (e.g. /blogs/post -> /blogs)
            parent_url = url.rsplit('/', 1)[0]
            if not parent_url: parent_url = "/"
            
            links.append({"source": parent_url, "target": url})

            # 3. The Ghost Product Trap
            # If it's a Shopify product with 0 impressions, sever its link so it becomes an Orphan!
            impressions = int(row.get('Impressions', 0))
            if impressions == 0 and "Shopify" in str(row.get('Source of Truth', '')):
                links.pop() # Remove the link we just added

    # Ensure all parent nodes exist so the math doesn't crash
    existing_urls = set([p['id'] for p in pages])
    for link in links:
        if link['source'] not in existing_urls:
            pages.append({"id": link['source'], "type": "Category", "traffic": 100})
            existing_urls.add(link['source'])
        if link['target'] not in existing_urls:
            pages.append({"id": link['target'], "type": "Category", "traffic": 100})
            existing_urls.add(link['target'])

    # Build the mathematical graph
    G = nx.DiGraph()
    for page in pages:
        G.add_node(page['id'], type=page.get('type', 'Other'), traffic=page['traffic'])
        
    for link in links:
        G.add_edge(link['source'], link['target'])

    # Run the PageRank Algorithm
    try:
        pagerank_scores = nx.pagerank(G, alpha=0.85)
    except:
        pagerank_scores = {node: 0.01 for node in G.nodes()}

    in_degrees = dict(G.in_degree())

    # Format for D3.js
    d3_nodes = []
    for node, data in G.nodes(data=True):
        is_orphan = (in_degrees.get(node, 0) == 0 and node != "/")
        
        d3_nodes.append({
            "id": node,
            "type": data['type'],
            "traffic": data['traffic'],
            "pagerank": pagerank_scores.get(node, 0.01) * 100,
            "is_orphan": is_orphan
        })

    return json.dumps({"nodes": d3_nodes, "links": links})