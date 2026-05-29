import json
import os
import re
import sys

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shopify_token_manager import get_validated_token

# ── Constants ─────────────────────────────────────────────────────────────────

BLOG_ID = 88906596673
STORE   = "95bd0d.myshopify.com"

SILO_RULES = [
    ("Saree",            ["saree", "sari"]),
    ("Kurti / Kurta",    ["kurti", "kurta", "kurtis"]),
    ("Lehenga",          ["lehenga"]),
    ("Co-ord Set",       ["co-ord", "coord"]),
    ("Suit / Salwar",    ["suit", "salwar", "dupatta", "anarkali"]),
    ("Indo-Western",     ["indo-western", "blazer", "formal-shirt"]),
    ("Wedding / Bridal", ["bridal", "wedding", "bride", "sherwani"]),
]

SILO_COLORS = {
    "Saree":            "#d97706",
    "Kurti / Kurta":    "#7c3aed",
    "Lehenga":          "#e11d48",
    "Co-ord Set":       "#0d9488",
    "Suit / Salwar":    "#2563eb",
    "Indo-Western":     "#16a34a",
    "Wedding / Bridal": "#db2777",
    "Other":            "#6b7280",
}

# None = no pillar defined yet for that silo
SILO_PILLARS = {
    "Saree":            "saree-for-women-complete-style-buying-guide-2026",
    "Kurti / Kurta":    None,
    "Lehenga":          None,
    "Co-ord Set":       None,
    "Suit / Salwar":    None,
    "Indo-Western":     None,
    "Wedding / Bridal": None,
    "Other":            None,
}

KNOWN_PILLAR_HANDLES = {"saree-for-women-complete-style-buying-guide-2026"}

DRAFT_QUEUE = [
    {"seq": 3, "id": 615812825409,
     "handle": "your-ultimate-buying-guide-to-dupattas-festive-wedding-styles-from-shree-shivam-raipur-nagpur",
     "keyword": "dupatta", "volume": 60500, "kd": 0, "note": "Next to publish"},
    {"seq": 4, "id": 615804928321,
     "handle": "shree-shivams-styling-guide-chic-suit-designs-for-every-woman-in-raipur-nagpur",
     "keyword": "suit design for women", "volume": 60500, "kd": 0, "note": "Publish same day as #5"},
    {"seq": 5, "id": 615804830017,
     "handle": "buying-guide-formal-shirts-for-women-mastering-professional-style-in-indias-tier-2-cities",
     "keyword": "formal shirts for women", "volume": 60500, "kd": 0, "note": "Publish same day as #4"},
    {"seq": 6, "id": 615804797249,
     "handle": "the-ultimate-styling-guide-double-breasted-suits-blazers-for-indian-weddings-modern-power-looks",
     "keyword": "double breasted suit", "volume": 60500, "kd": 0, "note": "Completes suit cluster"},
    {"seq": 7, "id": 615812890945,
     "handle": "2026-kurti-style-guide-5-fresh-designs-for-every-occasion-from-shree-shivam",
     "keyword": "kurti designs 2026", "volume": 27100, "kd": 0, "note": "HOLD — needs expansion"},
]

SAREE_PILLAR_PENDING = {
    "seq": 8, "handle": "saree-for-women-complete-style-buying-guide-2026",
    "keyword": "saree for women", "volume": 450000, "kd": 0,
    "note": "Publish LAST — file: content-drafts/saree-for-women-pillar-article.html",
}

# ── D3 template (single-silo view) ───────────────────────────────────────────
# Placeholders: __NODES__ __LINKS__ __MISSING__ __COLOR__ __SILO_NAME__

_D3_SINGLE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#0f172a; font-family:-apple-system,sans-serif; overflow:hidden; }
  svg  { display:block; }
  .node  { cursor:pointer; }
  .label { font-size:9px; fill:rgba(255,255,255,0.65); pointer-events:none; text-anchor:middle; }
  .link  { pointer-events:none; }
  .miss  { pointer-events:none; }
  #tip {
    position:fixed; background:rgba(8,15,30,0.97); color:#f1f5f9;
    padding:11px 14px; border-radius:9px; font-size:12px;
    pointer-events:none; display:none; max-width:300px;
    border:1px solid rgba(255,255,255,0.13); line-height:1.7;
    box-shadow:0 8px 30px rgba(0,0,0,0.7);
  }
  #hint { position:absolute; bottom:10px; right:14px; font-size:10px; color:rgba(255,255,255,0.28); }
  #stat { position:absolute; bottom:10px; left:14px; font-size:10px; color:rgba(255,255,255,0.35); }
  #leg  {
    position:absolute; top:12px; right:12px;
    background:rgba(8,15,30,0.82); border:1px solid rgba(255,255,255,0.1);
    border-radius:8px; padding:10px 14px; font-size:11px; color:rgba(255,255,255,0.7);
    line-height:1.9;
  }
</style>
</head>
<body>
<div style="position:relative;width:100%;height:660px">
  <svg id="sv" style="width:100%;height:660px"></svg>
  <div id="leg">
    <b style="color:__COLOR__">__SILO_NAME__</b><br>
    ● gold border = pillar<br>
    ● red glow = orphan<br>
    — solid = existing link<br>
    -- red dash = missing link<br>
    🔴 badge = gap count
  </div>
  <div id="stat"></div>
  <div id="hint">Hover · Click to highlight · Scroll to zoom · Drag</div>
</div>
<div id="tip"></div>

<script>
const NODES   = __NODES__;
const LINKS   = __LINKS__;
const MISSING = __MISSING__;
const COLOR   = "__COLOR__";

const svEl = document.getElementById('sv');
const W = svEl.getBoundingClientRect().width || 880;
const H = 660;
const svg = d3.select('#sv').attr('viewBox', [0,0,W,H]);
const root = svg.append('g');

svg.call(d3.zoom().scaleExtent([0.2,4]).on('zoom', e => root.attr('transform', e.transform)));

// Defs
const defs = svg.append('defs');

// Arrowhead for existing links
defs.append('marker').attr('id','arrow').attr('viewBox','0 -4 8 8')
  .attr('refX',22).attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto')
  .append('path').attr('d','M0,-4L8,0L0,4').attr('fill', COLOR).attr('opacity',0.7);

// Arrowhead for missing links
defs.append('marker').attr('id','arrow-miss').attr('viewBox','0 -4 8 8')
  .attr('refX',22).attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto')
  .append('path').attr('d','M0,-4L8,0L0,4').attr('fill','#ef4444').attr('opacity',0.8);

// Glow filters
function glow(id, col, blur) {
  const f = defs.append('filter').attr('id',id)
    .attr('x','-60%').attr('y','-60%').attr('width','220%').attr('height','220%');
  f.append('feGaussianBlur').attr('in','SourceGraphic').attr('stdDeviation',blur).attr('result','b');
  const m = f.append('feMerge');
  m.append('feMergeNode').attr('in','b');
  m.append('feMergeNode').attr('in','SourceGraphic');
}
glow('gr','#ef4444',6);
glow('gg','#fbbf24',7);
glow('gc', COLOR, 5);

// Seed positions
const pillarNode = NODES.find(n => n.is_pillar);
NODES.forEach(n => {
  if (n.is_pillar) { n.fx = W/2; n.fy = H/2; }
  else {
    n.x = W/2 + (Math.random()-0.5)*200;
    n.y = H/2 + (Math.random()-0.5)*200;
  }
});

function nr(d) { return d.is_pillar ? 17 : Math.max(8, 6 + d.inbound * 2.5); }

// Simulation
const allLinks = LINKS.concat(MISSING);
const sim = d3.forceSimulation(NODES)
  .force('link',    d3.forceLink(LINKS).id(d=>d.id).strength(0.25).distance(110))
  .force('charge',  d3.forceManyBody().strength(-220))
  .force('collide', d3.forceCollide(d => nr(d)+10))
  .force('center',  d3.forceCenter(W/2, H/2).strength(0.04))
  .force('bounds',  () => NODES.forEach(n => {
    n.x = Math.max(40, Math.min(W-40, n.x));
    n.y = Math.max(40, Math.min(H-40, n.y));
  }));

// Missing links layer (drawn first — behind)
const missG = root.append('g');
const missLine = missG.selectAll('line').data(MISSING).join('line').attr('class','miss')
  .attr('stroke','#ef4444').attr('stroke-opacity',0.55).attr('stroke-width',1.5)
  .attr('stroke-dasharray','6,4').attr('marker-end','url(#arrow-miss)');

// Existing links layer
const linkG = root.append('g');
const link = linkG.selectAll('line').data(LINKS).join('line').attr('class','link')
  .attr('stroke', COLOR).attr('stroke-opacity',0.5).attr('stroke-width',1.8)
  .attr('marker-end','url(#arrow)');

// Nodes
const nodeG = root.append('g');
const node = nodeG.selectAll('g').data(NODES).join('g').attr('class','node')
  .call(d3.drag()
    .on('start',(e,d)=>{ if(!e.active)sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
    .on('drag', (e,d)=>{ d.fx=e.x; d.fy=e.y; })
    .on('end',  (e,d)=>{ if(!e.active)sim.alphaTarget(0); if(!d.is_pillar){d.fx=null;d.fy=null;} }));

node.append('circle')
  .attr('r', nr)
  .attr('fill', COLOR)
  .attr('fill-opacity', d => d.is_draft ? 0.28 : 0.82)
  .attr('stroke', d => d.is_pillar ? '#fbbf24' : d.is_orphan ? '#ef4444' : d.gap_count>0 ? '#ef4444' : '#4ade80')
  .attr('stroke-width', d => (d.is_pillar||d.is_orphan||d.gap_count>0) ? 2.5 : 1.5)
  .attr('filter', d => d.is_pillar ? 'url(#gg)' : d.is_orphan ? 'url(#gr)' : null);

// Short label below node
node.append('text').attr('class','label')
  .attr('dy', d => nr(d)+11)
  .text(d => { const w=d.title.split(' '); return w.slice(0,3).join(' ')+(w.length>3?'…':''); });

// Gap badge
node.filter(d=>d.gap_count>0).append('circle')
  .attr('r',6).attr('cx',d=>nr(d)-3).attr('cy',d=>-nr(d)+3)
  .attr('fill','#ef4444').attr('stroke','#0f172a').attr('stroke-width',1.5);
node.filter(d=>d.gap_count>0).append('text')
  .attr('x',d=>nr(d)-3).attr('y',d=>-nr(d)+7)
  .attr('text-anchor','middle').attr('font-size',7).attr('fill','white').attr('pointer-events','none')
  .text(d=>d.gap_count);

// Tooltip + highlight
const tip = d3.select('#tip');
let active = null;

function setHL(d) {
  if (!d) {
    node.style('opacity',1);
    link.attr('stroke-opacity',0.5);
    missLine.attr('stroke-opacity',0.55);
    active=null; return;
  }
  const nb = new Set([d.id]);
  [...LINKS,...MISSING].forEach(l=>{
    const s=typeof l.source==='object'?l.source.id:l.source;
    const t=typeof l.target==='object'?l.target.id:l.target;
    if(s===d.id)nb.add(t);
    if(t===d.id)nb.add(s);
  });
  node.style('opacity', n => nb.has(n.id)?1:0.1);
  link.attr('stroke-opacity', l=>{
    const s=typeof l.source==='object'?l.source.id:l.source;
    const t=typeof l.target==='object'?l.target.id:l.target;
    return (s===d.id||t===d.id)?0.85:0.04;
  });
  missLine.attr('stroke-opacity', l=>{
    const s=typeof l.source==='object'?l.source.id:l.source;
    const t=typeof l.target==='object'?l.target.id:l.target;
    return (s===d.id||t===d.id)?0.85:0.04;
  });
  active=d.id;
}

node
  .on('mouseover',(ev,d)=>{
    const gHtml = d.gap_count>0
      ? `<div style="color:#f87171;margin-top:5px">⚠ ${d.missing.map(m=>'<br>• '+m).join('')}</div>`
      : `<div style="color:#4ade80;margin-top:5px">✓ All cluster links present</div>`;
    const badges=[
      d.is_pillar?'<span style="color:#fbbf24">★ Pillar</span>':'',
      d.is_draft ?'<span style="color:#94a3b8">Draft</span>':'',
      d.is_orphan?'<span style="color:#f87171">Orphan</span>':'',
    ].filter(Boolean).join(' · ');
    tip.style('display','block')
      .style('left',(ev.clientX+14)+'px').style('top',(ev.clientY-14)+'px')
      .html(`
        <div style="font-weight:600;margin-bottom:3px">${d.title}</div>
        ${badges?`<div style="font-size:11px;margin-bottom:3px">${badges}</div>`:''}
        <div style="color:rgba(255,255,255,0.5);font-size:11px">↙ ${d.inbound} in · ↗ ${d.outbound} out · ${d.words} words</div>
        ${gHtml}
      `);
  })
  .on('mousemove',ev=>tip.style('left',(ev.clientX+14)+'px').style('top',(ev.clientY-14)+'px'))
  .on('mouseout', ()=>tip.style('display','none'))
  .on('click',(ev,d)=>{ ev.stopPropagation(); active===d.id?setHL(null):setHL(d); });

svg.on('click',()=>setHL(null));

// Tick
sim.on('tick',()=>{
  [link,missLine].forEach(sel=>{
    sel.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
       .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
  });
  node.attr('transform',d=>`translate(${d.x.toFixed(1)},${d.y.toFixed(1)})`);
});

// Stats footer
const live  = NODES.filter(n=>n.is_live).length;
const gaps  = NODES.reduce((s,n)=>s+n.gap_count,0);
const orph  = NODES.filter(n=>n.is_orphan).length;
const miss  = MISSING.length;
document.getElementById('stat').textContent =
  `${live} live · ${NODES.filter(n=>n.is_draft).length} draft · ${orph} orphan · ${gaps} gaps · ${miss} missing links shown`;
</script>
</body>
</html>"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def classify_silo(handle: str, title: str = "") -> str:
    text = (handle + " " + title).lower()
    for silo, keywords in SILO_RULES:
        if any(kw in text for kw in keywords):
            return silo
    return "Other"


def extract_blog_links(body_html: str) -> list:
    if not body_html:
        return []
    pat = re.compile(r'href=["\'][^"\']*?/blogs/blog/([^"\'/?#\s]+)', re.IGNORECASE)
    seen, result = set(), []
    for m in pat.finditer(body_html):
        h = m.group(1).strip("/")
        if h and h not in seen:
            seen.add(h); result.append(h)
    return result


def word_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(re.sub(r"\s+", " ", text).strip().split()) if text.strip() else 0


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_articles() -> list:
    token, _ = get_validated_token()
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    r = requests.get(
        f"https://{STORE}/admin/api/2024-01/blogs/{BLOG_ID}/articles.json"
        "?limit=250&fields=id,handle,title,body_html,published_at",
        headers=headers, timeout=30,
    )
    r.raise_for_status()
    return r.json().get("articles", [])


def build_graph(articles: list) -> pd.DataFrame:
    handle_set = {a["handle"] for a in articles}
    rows = []
    for a in articles:
        lo = [h for h in extract_blog_links(a.get("body_html", "")) if h in handle_set]
        rows.append({
            "id": a["id"], "handle": a["handle"], "title": a["title"],
            "silo": classify_silo(a["handle"], a["title"]),
            "is_live": a.get("published_at") is not None,
            "is_pillar": a["handle"] in KNOWN_PILLAR_HANDLES,
            "words": word_count(a.get("body_html", "")),
            "links_out": lo, "out_count": len(lo),
        })
    df = pd.DataFrame(rows)
    inbound      = {h: 0  for h in handle_set}
    inbound_from = {h: [] for h in handle_set}
    for r in rows:
        for t in r["links_out"]:
            inbound[t] += 1; inbound_from[t].append(r["handle"])
    df["in_count"]  = df["handle"].map(inbound)
    df["in_from"]   = df["handle"].map(inbound_from)
    df["is_orphan"] = (df["in_count"] == 0) & df["is_live"]
    return df


def compute_cluster_gaps(df: pd.DataFrame) -> dict:
    handle_to_silo  = dict(zip(df["handle"], df["silo"]))
    handle_to_links = dict(zip(df["handle"], df["links_out"]))
    live_handles    = set(df.loc[df["is_live"], "handle"])
    results = {}

    for _, row in df.iterrows():
        handle, silo = row["handle"], row["silo"]
        links_out    = set(row["links_out"])
        missing      = []
        pillar_handle = SILO_PILLARS.get(silo)
        pillar_live   = pillar_handle and pillar_handle in live_handles

        to_pillar = from_pillar = None
        if pillar_handle and handle != pillar_handle:
            if pillar_live:
                to_pillar = pillar_handle in links_out
                if not to_pillar:
                    missing.append(f"Link → pillar: {pillar_handle}")
                pillar_links = set(handle_to_links.get(pillar_handle, []))
                from_pillar  = handle in pillar_links
                if not from_pillar:
                    missing.append("Pillar needs to link → this article")

        siblings = {h for h, s in handle_to_silo.items()
                    if s == silo and h != handle and h != pillar_handle}
        to_sibling = None
        if siblings:
            to_sibling = bool(links_out & siblings)
            if not to_sibling:
                best = df[df["handle"].isin(siblings)].sort_values("in_count", ascending=False)
                sug  = best.iloc[0]["handle"] if not best.empty else "a sibling article"
                missing.append(f"Link → silo sibling (e.g. {sug})")

        results[handle] = {
            "to_pillar": to_pillar, "from_pillar": from_pillar,
            "to_sibling": to_sibling, "gap_count": len(missing), "missing": missing,
        }
    return results


# ── D3 builder (single silo) ──────────────────────────────────────────────────

def _build_silo_d3(silo_df: pd.DataFrame, gaps: dict, silo: str) -> str:
    color = SILO_COLORS.get(silo, "#6b7280")
    handle_set = set(silo_df["handle"])
    pillar_handle = SILO_PILLARS.get(silo)
    live_handles  = set(silo_df.loc[silo_df["is_live"], "handle"])

    nodes = []
    for _, row in silo_df.iterrows():
        g = gaps.get(row["handle"], {"gap_count": 0, "missing": []})
        nodes.append({
            "id": row["handle"], "title": row["title"],
            "inbound": int(row["in_count"]), "outbound": int(row["out_count"]),
            "is_live": bool(row["is_live"]), "is_draft": not bool(row["is_live"]),
            "is_pillar": bool(row["is_pillar"]), "is_orphan": bool(row["is_orphan"]),
            "gap_count": g["gap_count"], "missing": g["missing"], "words": int(row["words"]),
        })

    # Existing links (only within this silo)
    links = []
    for _, row in silo_df.iterrows():
        for t in row["links_out"]:
            if t in handle_set:
                links.append({"source": row["handle"], "target": t})

    # Missing pillar links (draw as red dashes)
    missing_links = []
    if pillar_handle and pillar_handle in live_handles:
        pillar_links_out = set(
            silo_df.loc[silo_df["handle"] == pillar_handle, "links_out"].iloc[0]
            if not silo_df[silo_df["handle"] == pillar_handle].empty else []
        )
        for _, row in silo_df.iterrows():
            h = row["handle"]
            if h == pillar_handle:
                continue
            g = gaps.get(h, {})
            if g.get("to_pillar") is False:
                missing_links.append({"source": h, "target": pillar_handle})
            if g.get("from_pillar") is False:
                missing_links.append({"source": pillar_handle, "target": h})

    html = _D3_SINGLE
    html = html.replace("__NODES__",     json.dumps(nodes))
    html = html.replace("__LINKS__",     json.dumps(links))
    html = html.replace("__MISSING__",   json.dumps(missing_links))
    html = html.replace("__COLOR__",     color)
    html = html.replace("__SILO_NAME__", silo)
    return html


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_all_silo_summary(df: pd.DataFrame, gaps: dict):
    """Compact top-level table — one row per silo."""
    silos = sorted(df["silo"].unique())
    handle_to_silo = dict(zip(df["handle"], df["silo"]))
    rows = []
    for silo in silos:
        sdf  = df[df["silo"] == silo]
        live = sdf[sdf["is_live"]]
        silo_gap = sum(gaps.get(h, {}).get("gap_count", 0) for h in sdf["handle"])
        pillar   = SILO_PILLARS.get(silo)
        pillar_status = (
            "✓ Live"   if pillar and not sdf[(sdf["handle"]==pillar)&sdf["is_live"]].empty
            else "⏳ Pending" if pillar
            else "— None"
        )
        rows.append({
            "Silo":     silo,
            "Live":     len(live),
            "Draft":    len(sdf) - len(live),
            "Pillar":   pillar_status,
            "Orphans":  int(live["is_orphan"].sum()),
            "Gaps":     silo_gap,
            "Status":   "🟢 Clean" if silo_gap == 0 else f"🔴 {silo_gap} gaps",
        })

    summary = pd.DataFrame(rows)

    def _sty(row):
        s = [""] * len(row)
        gi = list(row.index).index("Gaps")
        pi = list(row.index).index("Pillar")
        si = list(row.index).index("Status")
        oi = list(row.index).index("Orphans")
        if row["Gaps"] > 0:
            s[gi] = "color:#f87171;font-weight:bold"
            s[si] = "color:#f87171"
        else:
            s[si] = "color:#4ade80"
        if "✓" in str(row["Pillar"]):
            s[pi] = "color:#4ade80"
        elif "Pending" in str(row["Pillar"]):
            s[pi] = "color:#fbbf24"
        else:
            s[pi] = "color:#64748b"
        if row["Orphans"] > 0:
            s[oi] = "color:#f87171"
        return s

    st.dataframe(
        summary.style.apply(_sty, axis=1),
        use_container_width=True,
        hide_index=True,
        height=min(36 * (len(rows) + 2), 380),
    )


def _render_silo_detail(silo_df: pd.DataFrame, silo_gaps: dict, silo: str):
    color = SILO_COLORS.get(silo, "#6b7280")
    live  = silo_df[silo_df["is_live"]]
    draft = silo_df[~silo_df["is_live"]]
    total_gaps   = sum(g["gap_count"] for g in silo_gaps.values())
    pillar_handle = SILO_PILLARS.get(silo)
    pillar_live   = pillar_handle and not silo_df[
        (silo_df["handle"] == pillar_handle) & silo_df["is_live"]
    ].empty

    # Silo-level metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Articles", len(live))
    c2.metric("Drafts",   len(draft))
    c3.metric("Cluster Gaps", total_gaps)
    c4.metric("Orphans",  int(live["is_orphan"].sum()))
    c5.metric(
        "Pillar",
        "✓ Live"    if pillar_live
        else "⏳ Pending" if pillar_handle
        else "None defined",
    )

    st.divider()

    tab_map, tab_gaps = st.tabs(["🫧 Bubble Map", "🔍 Cluster Gaps"])

    with tab_map:
        st.caption(
            f"Articles in the **{silo}** silo. "
            "Solid lines = existing links. "
            "Red dashes = missing pillar links. "
            "Red border = has gaps. Green border = clean."
        )
        html = _build_silo_d3(silo_df, silo_gaps, silo)
        components.html(html, height=680, scrolling=False)

    with tab_gaps:
        _render_gap_table(silo_df, silo_gaps, silo)


def _render_gap_table(silo_df: pd.DataFrame, silo_gaps: dict, silo: str):
    st.caption(
        "**→ Pillar**: does this article link UP to the silo pillar?  "
        "**Pillar →**: does the pillar link DOWN to this article?  "
        "**→ Sibling**: does it link to at least one other article in this silo?"
    )

    pillar = SILO_PILLARS.get(silo)
    rows   = []
    for _, row in silo_df.iterrows():
        g = silo_gaps.get(row["handle"], {})
        pillar_note = " ⏳" if pillar and not silo_df[
            (silo_df["handle"] == pillar) & silo_df["is_live"]
        ].empty is False else ""

        def icon(v):
            if v is True:  return "✓"
            if v is False: return "✗"
            return "—"

        rows.append({
            "Article":   row["handle"],
            "Live":      "✓" if row["is_live"] else "📝",
            "→ Pillar":  (icon(g.get("to_pillar")) + pillar_note) if pillar else "— no pillar",
            "Pillar →":  (icon(g.get("from_pillar")) + pillar_note) if pillar else "— no pillar",
            "→ Sibling": icon(g.get("to_sibling")),
            "Gaps":      g.get("gap_count", 0),
            "Fix":       " | ".join(g.get("missing", [])) or "—",
        })

    if not rows:
        st.info("No articles in this silo yet.")
        return

    table = pd.DataFrame(rows)

    def _sty(row):
        s = [""] * len(row)
        gi  = list(row.index).index("Gaps")
        fi  = list(row.index).index("Fix")
        for col_name in ["→ Pillar", "Pillar →", "→ Sibling"]:
            if col_name in row.index:
                ci = list(row.index).index(col_name)
                v  = str(row[col_name])
                if v.startswith("✗"):   s[ci] = "color:#f87171;font-weight:bold"
                elif v.startswith("✓"): s[ci] = "color:#4ade80"
                else:                   s[ci] = "color:#64748b"
        s[gi] = "color:#f87171;font-weight:bold" if row["Gaps"] > 0 else "color:#4ade80"
        if row["Gaps"] > 0:
            s[fi] = "color:#fbbf24;font-size:11px"
        return s

    st.dataframe(
        table.style.apply(_sty, axis=1),
        use_container_width=True,
        height=min(40 * (len(rows) + 2), 520),
        hide_index=True,
        column_config={
            "Article": st.column_config.TextColumn(width="large"),
            "Fix":     st.column_config.TextColumn("Fix Needed", width="large"),
        },
    )

    # Priority actions
    urgent = [(h, g) for h, g in silo_gaps.items() if g.get("gap_count", 0) > 0]
    urgent.sort(key=lambda x: -x[1]["gap_count"])
    if urgent:
        st.markdown("**Actions to close the gaps:**")
        for handle, g in urgent:
            for fix in g["missing"]:
                st.markdown(f"- `{handle[:60]}` → {fix}")


def _render_publish_queue(draft_df: pd.DataFrame):
    st.subheader("Draft Publish Queue")
    st.caption("Priority = Volume ÷ (KD+1). Suit cluster (#4+#5+#6) must publish within 48 h.")

    draft_handles = set(draft_df["handle"].tolist()) if not draft_df.empty else set()
    draft_words   = dict(zip(draft_df["handle"], draft_df["words"])) if not draft_df.empty else {}

    rows = []
    for d in DRAFT_QUEUE:
        rows.append({
            "#":      d["seq"],
            "Keyword":d["keyword"],
            "Vol":    f"{d['volume']:,}",
            "KD":     d["kd"],
            "Words":  draft_words.get(d["handle"], "?"),
            "Score":  f"{d['volume']/(d['kd']+1):,.0f}",
            "Status": "Draft" if d["handle"] in draft_handles else "Published ✓",
            "Note":   d["note"],
        })

    p = SAREE_PILLAR_PENDING
    rows.append({
        "#": p["seq"], "Keyword": p["keyword"],
        "Vol": f"{p['volume']:,}", "KD": p["kd"],
        "Words": "~2,000", "Score": f"{p['volume']:,}",
        "Status": "Pending upload", "Note": p["note"],
    })

    def _sty(row):
        s = [""] * len(row)
        si = list(row.index).index("Status")
        ni = list(row.index).index("Note")
        if "Published" in str(row["Status"]): s[si] = "color:#4ade80;font-weight:bold"
        elif "Pending"  in str(row["Status"]): s[si] = "color:#fbbf24;font-weight:bold"
        if "HOLD" in str(row["Note"]): s[ni] = "color:#f87171"
        return s

    st.dataframe(
        pd.DataFrame(rows).style.apply(_sty, axis=1),
        use_container_width=True, hide_index=True,
    )
    st.info("**Suit cluster:** Publish #4, #5, #6 within 48 h for topical authority signal.")
    st.info("**Saree pillar (#8):** Upload `content-drafts/saree-for-women-pillar-article.html` only after all 7 drafts are live.")


# ── Main render ───────────────────────────────────────────────────────────────

def render(master_df, notion_df):
    st.title("🏗️ Blog Silo & Cluster Gap Audit")
    st.caption("Select a silo below to inspect its internal link structure and cluster gaps.")

    with st.spinner("Loading articles from Shopify..."):
        try:
            articles = fetch_articles()
        except Exception as e:
            st.error(f"Shopify fetch failed: {e}")
            return

    df   = build_graph(articles)
    gaps = compute_cluster_gaps(df)

    # ── All-silo summary ──
    with st.expander("📊 All Silos — Health Summary", expanded=True):
        _render_all_silo_summary(df, gaps)

    st.divider()

    # ── Silo selector with gap counts ──
    silos = sorted(df["silo"].unique().tolist())

    def silo_label(s):
        g = sum(gaps.get(h, {}).get("gap_count", 0) for h in df.loc[df["silo"]==s, "handle"])
        return f"{s}  ({g} gaps)" if g else f"{s}  ✓"

    labels     = [silo_label(s) for s in silos]
    label_map  = dict(zip(labels, silos))

    selected_label = st.radio(
        "Select silo to inspect:",
        labels,
        horizontal=True,
        key="silo_radio",
    )
    selected_silo  = label_map[selected_label]
    color          = SILO_COLORS.get(selected_silo, "#6b7280")

    st.markdown(
        f"<h3 style='color:{color};margin-top:12px'>{selected_silo} Silo</h3>",
        unsafe_allow_html=True,
    )

    silo_df   = df[df["silo"] == selected_silo].copy()
    silo_gaps = {h: g for h, g in gaps.items() if h in set(silo_df["handle"])}

    _render_silo_detail(silo_df, silo_gaps, selected_silo)

    st.divider()

    # ── Publish queue always at bottom ──
    with st.expander("🚀 Draft Publish Queue", expanded=False):
        _render_publish_queue(df[~df["is_live"]])


if __name__ == "__main__":
    render(pd.DataFrame(), pd.DataFrame())
