# Shree Shivam: Custom SEO Analysis Engine 🚀

## Overview
A custom-built, Python-driven SEO intelligence engine designed to move beyond standard reporting ("what happened") into automated, algorithmic analysis ("why it happened and what to do next"). 

This tool merges real-time API data, static exports, and manual SEO edit logs to visualize semantic gaps and internal linking structures using D3.js.

## Tech Stack
*   **Backend / Data Processing:** Python (Pandas, NumPy)
*   **Algorithms:** spaCy/NLTK (Semantic NLP), NetworkX (Internal PageRank)
*   **Presentation Layer:** Streamlit (Web App Framework)
*   **Visualizations:** Plotly & Custom D3.js (Network Graphs)

## Data Sources
1.  **Google Search Console (GSC):** Primary traffic & keyword performance.
2.  **Google Analytics 4 (GA4):** User behavior & conversions.
3.  **DataForSEO / SEMrush:** Competitor SERP data, keyword gaps, and backlink audits.
4.  **Notion API:** The "Control Center" log of manual SEO edits (to trace impact over time).
5.  **Site Crawler (e.g., Screaming Frog / Custom Python Crawler):** Internal linking topography.

## Core Features (Algorithms)
*   **The Action Matrix (Treasure Map):** Algorithmic filtering of GSC + GA4 data to automatically flag URLs needing specific actions (Striking Distance, Leaky Buckets, Hidden Gems).
*   **Micro Semantic Analysis:** TF-IDF and NLP entity extraction comparing our pages against top 10 SERP competitors.
*   **Macro Semantic Clusters:** Grouping URLs by topic to detect cluster-wide authority decay.
*   **Internal PageRank Topology:** D3.js force-directed graphs to identify orphaned pages, semantic leaks, and opportunities for link juice flow.
*   **Action-to-Impact Tracing:** Correlating timestamps from the Notion SEO Edits database to GSC traffic spikes.

---

## 🗺️ Project Roadmap

### Phase 1: The Data Pipeline (Ingestion & Merging)
- [x] Set up local Python environment and directory structure.
- [ ] Build ingestion script for static files (SEMrush CSVs, Screaming Frog exports).
- [x] Build API connection for GSC / GA4.
- [x] Build API connection for Notion Edits Tracker.
- [x] Create the "Master DataFrame" (merging all data on the `URL` primary key).

### Phase 2: The Analysis Engine (Algorithms)
- [x] Develop Action Matrix (Treasure Map) filtering logic.
- [x] Develop Internal PageRank scoring via `networkx` (Core math built, awaiting CSV data).
- [ ] Develop Topic Clustering logic.
- [ ] Develop Competitor Semantic Gap analysis (Micro Semantics).

### Phase 3: The Presentation Layer (Streamlit + D3)
- [x] Initialize Streamlit `app.py` and layout routing.
- [x] Build the standard Data Tables and metric cards.
- [x] Integrate custom D3.js force-directed graph for internal linking.

### Phase 4: Automation & Deployment
- [ ] Finalize `.env` vault for all API keys.
- [ ] (Optional) Deploy to a secure server or Streamlit Community Cloud.

---
*Last Updated: May 2026*