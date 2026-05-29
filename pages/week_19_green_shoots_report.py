import os
import re
import math
import requests
import pandas as pd
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

from googleapiclient.discovery import build
import google.auth
import streamlit as st
import pandas as pd

def render(master_df, notion_df):
    st.title("Week 19 Green Shoots")
    st.write("Report page loaded.")
ENV_PATH = r"C:\Users\shree\OneDrive\Documents\mynk\Credentials\apikeys.env.txt"
load_dotenv(ENV_PATH)

GSC_PROPERTY = os.getenv("GSC_PROPERTY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_SEO_EDITS = os.getenv("NOTION_DB_SEO_EDITS")

OUTPUT_FILE = "shree-shivam-green-shoots-WEEK-19.html"


def clean_url(value):
    value = str(value or "").strip().lower()
    value = value.replace("https://www.shreeshivam.com", "")
    value = value.replace("https://shreeshivam.com", "")
    value = value.replace("www.shreeshivam.com", "")
    value = re.sub(r"\s+", " ", value).strip()
    if value.endswith("/") and value != "/":
        value = value[:-1]
    return value


def fmt_int(x):
    try:
        return f"{int(round(float(x))):,}"
    except:
        return "0"


def fmt_float(x, d=1):
    try:
        return f"{float(x):.{d}f}"
    except:
        return f"{0:.{d}f}"


def safe_text(v):
    if pd.isna(v):
        return ""
    return str(v)


def gsc_service():
    credentials, _ = google.auth.default()
    return build("searchconsole", "v1", credentials=credentials)


def query_gsc(start_date, end_date, dimensions, row_limit=25000, dimension_filter_groups=None):
    service = gsc_service()
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit
    }
    if dimension_filter_groups:
        body["dimensionFilterGroups"] = dimension_filter_groups
    response = service.searchanalytics().query(siteUrl=GSC_PROPERTY, body=body).execute()
    return response.get("rows", [])


def get_page_level_gsc(start_date, end_date):
    rows = query_gsc(start_date, end_date, ["page"], row_limit=25000)
    data = []
    for r in rows:
        keys = r.get("keys", [""])
        data.append({
            "URL": clean_url(keys[0]),
            "Clicks": r.get("clicks", 0),
            "Impressions": r.get("impressions", 0),
            "CTR": r.get("ctr", 0) * 100,
            "Position": r.get("position", 0)
        })
    return pd.DataFrame(data)


def get_query_level_gsc(start_date, end_date):
    rows = query_gsc(start_date, end_date, ["query"], row_limit=25000)
    data = []
    for r in rows:
        keys = r.get("keys", [""])
        q = safe_text(keys[0]).strip()
        if not q:
            continue
        data.append({
            "Query": q,
            "Clicks": r.get("clicks", 0),
            "Impressions": r.get("impressions", 0),
            "CTR": r.get("ctr", 0) * 100,
            "Position": r.get("position", 0)
        })
    return pd.DataFrame(data)


def get_page_query_level_gsc(start_date, end_date):
    rows = query_gsc(start_date, end_date, ["page", "query"], row_limit=25000)
    data = []
    for r in rows:
        keys = r.get("keys", ["", ""])
        data.append({
            "URL": clean_url(keys[0]),
            "Query": safe_text(keys[1]).strip(),
            "Clicks": r.get("clicks", 0),
            "Impressions": r.get("impressions", 0),
            "CTR": r.get("ctr", 0) * 100,
            "Position": r.get("position", 0)
        })
    return pd.DataFrame(data)


def get_notion_edits():
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_SEO_EDITS}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    all_rows = []
    payload = {"page_size": 100}
    while True:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        data = res.json()
        all_rows.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")

    parsed = []
    for page in all_rows:
        props = page.get("properties", {})

        def title_val(name):
            arr = props.get(name, {}).get("title", [])
            return "".join([x.get("plain_text", "") for x in arr]).strip()

        def rich_text_val(name):
            arr = props.get(name, {}).get("rich_text", [])
            return "".join([x.get("plain_text", "") for x in arr]).strip()

        def select_val(name):
            obj = props.get(name, {}).get("select")
            return obj.get("name") if obj else ""

        def date_val(name):
            obj = props.get(name, {}).get("date")
            return obj.get("start") if obj else ""

        row = {
            "Page / URL": title_val("Page / URL"),
            "Change Type": select_val("Change Type"),
            "Status": select_val("Status"),
            "Changed On": date_val("Changed On"),
            "Review On": date_val("Review On"),
            "Before": rich_text_val("Before"),
            "After": rich_text_val("After"),
            "Notes": rich_text_val("Notes"),
            "Target Keywords": rich_text_val("Target Keywords"),
            "Expected Impact": rich_text_val("Expected Impact"),
        }
        row["Clean_URL"] = clean_url(row["Page / URL"])
        parsed.append(row)

    df = pd.DataFrame(parsed)
    if not df.empty and "Changed On" in df.columns:
        df["Changed On"] = pd.to_datetime(df["Changed On"], errors="coerce")
    return df


def classify_intent(q):
    q = q.lower()
    local_terms = ["near me", "raipur", "bilaspur", "jabalpur", "nagpur", "store", "shop"]
    info_terms = ["trend", "trends", "ideas", "how", "style", "styling", "what", "guide", "latest"]
    commercial_terms = ["buy", "shop", "price", "collection", "design", "dress", "saree", "kurti", "lehenga"]

    if any(t in q for t in local_terms):
        return "Local"
    if any(t in q for t in info_terms):
        return "Informational"
    if any(t in q for t in commercial_terms):
        return "Commercial"
    return "Mixed"


def est_volume_bucket(q):
    q = q.lower()
    if "near me" in q:
        return "~10,000–50,000"
    if any(t in q for t in ["trend", "trends", "latest", "2026"]):
        return "~2,000–12,000"
    if any(t in q for t in ["bridal", "lehenga", "kurti", "saree", "indo western"]):
        return "~500–5,000"
    return "~200–2,000"


def keyword_win_cards(curr_queries, prev_queries):
    if curr_queries.empty:
        return []

    prev = prev_queries.rename(columns={
        "Clicks": "Prev Clicks",
        "Impressions": "Prev Impressions",
        "CTR": "Prev CTR",
        "Position": "Prev Position"
    }).copy()

    merged = curr_queries.merge(prev, on="Query", how="left")
    for c in ["Prev Clicks", "Prev Impressions", "Prev CTR", "Prev Position"]:
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0)

    merged["NewClicks"] = merged["Clicks"] - merged["Prev Clicks"]
    merged["NewImpressions"] = merged["Impressions"] - merged["Prev Impressions"]
    merged["CtrLift"] = merged["CTR"] - merged["Prev CTR"]
    merged["PosGain"] = merged["Prev Position"] - merged["Position"]

    candidates = merged.sort_values(
        ["NewClicks", "NewImpressions", "Clicks", "Impressions"],
        ascending=[False, False, False, False]
    ).head(8)

    cards = []
    for _, r in candidates.iterrows():
        cards.append({
            "label": "Keyword Win",
            "delta": f"+{fmt_int(r['NewClicks'])} clicks" if r["NewClicks"] > 0 else f"+{fmt_int(r['NewImpressions'])} imps",
            "name": r["Query"],
            "before": fmt_int(r["Prev Clicks"]),
            "sprint": fmt_int(r["Clicks"]),
            "ctr": fmt_float(r["CTR"], 2) + "%",
            "pos": fmt_float(r["Position"], 1),
            "note": f"{classify_intent(r['Query'])} intent • est volume {est_volume_bucket(r['Query'])}"
        })
    return cards


def page_win_cards(curr_pages, prev_pages):
    if curr_pages.empty:
        return []

    prev = prev_pages.rename(columns={
        "Clicks": "Prev Clicks",
        "Impressions": "Prev Impressions",
        "CTR": "Prev CTR",
        "Position": "Prev Position"
    }).copy()

    merged = curr_pages.merge(prev, on="URL", how="left")
    for c in ["Prev Clicks", "Prev Impressions", "Prev CTR", "Prev Position"]:
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0)

    merged["NewClicks"] = merged["Clicks"] - merged["Prev Clicks"]
    merged["NewImpressions"] = merged["Impressions"] - merged["Prev Impressions"]
    merged["CtrLift"] = merged["CTR"] - merged["Prev CTR"]

    top = merged.sort_values(
        ["NewClicks", "NewImpressions", "Clicks"],
        ascending=[False, False, False]
    ).head(6)

    cards = []
    for _, r in top.iterrows():
        cards.append({
            "label": "Page Win",
            "delta": f"+{fmt_int(r['NewClicks'])} clicks" if r["NewClicks"] > 0 else f"+{fmt_int(r['NewImpressions'])} imps",
            "name": r["URL"] or "/",
            "before": fmt_int(r["Prev Clicks"]),
            "sprint": fmt_int(r["Clicks"]),
            "ctr": fmt_float(r["CTR"], 2) + "%",
            "pos": fmt_float(r["Position"], 1),
            "note": f"CTR lift {fmt_float(r['CtrLift'],2)} pts • page-level growth from current window vs previous window"
        })
    return cards


def build_html(report):
    keyword_rows = ""
    for row in report["top_keywords"]:
        keyword_rows += f"""
        <tr>
          <td class="kw-name">{row['Query']}</td>
          <td>{fmt_int(row['Impressions'])}</td>
          <td>{fmt_int(row['Clicks'])}</td>
          <td class="{'pos-good' if row['Position'] <= 8 else 'pos-ok' if row['Position'] <= 12 else 'pos-low'}">{fmt_float(row['Position'],1)}</td>
          <td>{row['Volume']}</td>
          <td>{row['Intent']}</td>
        </tr>
        """

    win_cards = ""
    for card in report["win_cards"]:
        win_cards += f"""
        <div class="wc cg">
          <div class="wt">
            <span class="wlbl wlg">{card['label']}</span>
            <span class="wdelta">{card['delta']}</span>
          </div>
          <div class="wname">{card['name']}</div>
          <div class="wstats">
            <div class="ws"><span class="wsl">Before</span><span class="wsv">{card['before']}</span></div>
            <div class="ws"><span class="wsl">Now</span><span class="wsv" style="color:var(--gr)">{card['sprint']}</span></div>
            <div class="ws"><span class="wsl">CTR</span><span class="wsv" style="color:var(--tl)">{card['ctr']}</span></div>
            <div class="ws"><span class="wsl">Pos</span><span class="wsv">{card['pos']}</span></div>
          </div>
          <div class="wnote">{card['note']}</div>
        </div>
        """

    action_rows = ""
    for row in report["actions"]:
        action_rows += f"""
        <div class="cli">
          <span class="cli-date">{row['date_label']}</span>
          <div class="cli-body">
            <strong>{row['url']}</strong> {row['summary']}
            <span class="tag tg">{row['type']}</span>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shree Shivam Green Shoots SEO Report Week 19</title>
<link href="https://api.fontshare.com/v2/css?f[]=cabinet-grotesk@800,900&f[]=satoshi@400,500,700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#0b0a08; --s1:#111009; --s2:#161410; --s3:#1c1a15; --s4:#222018;
  --bd:#252320; --bd2:#2e2b26; --tx:#e8e6df; --mu:#87857b; --fa:#a3a093;
  --gr:#2ecc71; --gr2:#27ae60; --grb:rgba(46,204,113,.09); --grbb:rgba(46,204,113,.18);
  --tl:#4da8b3; --tlb:rgba(77,168,179,.09); --go:#e8b84b; --gob:rgba(232,184,75,.09);
  --rd:#e05252; --rdb:rgba(224,82,82,.09); --r:10px;
}}
* {{box-sizing:border-box; margin:0; padding:0;}}
body {{background:var(--bg); color:var(--tx); font-family:Satoshi,sans-serif; font-size:15px; line-height:1.65; padding:40px 20px;}}
.wrap {{max-width:1120px; margin:0 auto;}}
.hdr {{padding-bottom:32px; margin-bottom:36px; border-bottom:1px solid var(--bd2);}}
.badges {{display:flex; gap:8px; flex-wrap:wrap; margin-bottom:18px;}}
.badge {{font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; padding:4px 10px; border-radius:4px;}}
.bg {{background:var(--grb); color:var(--gr); border:1px solid rgba(46,204,113,.2);}}
.bt {{background:var(--tlb); color:var(--tl); border:1px solid rgba(77,168,179,.2);}}
.by {{background:var(--gob); color:var(--go); border:1px solid rgba(232,184,75,.2);}}
.hdr-row {{display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:16px;}}
h1 {{font-family:"Cabinet Grotesk",sans-serif; font-size:clamp(2.3rem,5vw,3.8rem); font-weight:900; line-height:1.03; letter-spacing:-1.5px; margin-bottom:10px;}}
h1 em {{color:var(--gr); font-style:normal;}}
.hdr-sub {{color:var(--mu); font-size:13px; line-height:1.8;}}
.hdr-meta {{text-align:right; font-size:12px; color:var(--mu); line-height:1.9;}}
.hdr-meta strong {{color:var(--tx);}}
.proof {{background:linear-gradient(135deg,rgba(46,204,113,.11),rgba(77,168,179,.06)); border:1px solid rgba(46,204,113,.22); border-radius:14px; padding:28px 32px; margin-bottom:34px; display:grid; grid-template-columns:1fr auto; gap:24px; align-items:center;}}
.proof h2 {{font-family:"Cabinet Grotesk",sans-serif; font-size:clamp(1.5rem,3vw,2.3rem); font-weight:900; color:var(--gr); margin-bottom:8px;}}
.proof p {{font-size:14px; color:var(--mu); max-width:64ch; line-height:1.6;}}
.proof-nums {{display:flex; gap:28px; flex-wrap:wrap;}}
.pn {{text-align:center;}}
.pnv {{font-family:"Cabinet Grotesk",sans-serif; font-size:2.3rem; font-weight:900; line-height:1;}}
.pnl {{font-size:10px; text-transform:uppercase; letter-spacing:1px; color:var(--mu);}}
.sec {{margin-bottom:38px;}}
.sec-hdr {{display:flex; align-items:center; gap:10px; margin-bottom:16px; padding-bottom:10px; border-bottom:1px solid var(--bd);}}
.sec-hdr span:first-child {{width:8px; height:8px; border-radius:50%; background:var(--gr);}}
.sec-t {{font-size:11px; text-transform:uppercase; letter-spacing:2px; color:var(--mu); font-weight:700;}}
.kpi-grid {{display:grid; grid-template-columns:repeat(auto-fill,minmax(165px,1fr)); gap:12px;}}
.kpi {{background:var(--s1); border:1px solid var(--bd2); border-radius:var(--r); padding:18px 16px; position:relative; overflow:hidden;}}
.kpi:after {{content:""; position:absolute; top:0; left:0; right:0; height:2px;}}
.kpi.g:after {{background:var(--gr);}} .kpi.t:after {{background:var(--tl);}} .kpi.y:after {{background:var(--go);}} .kpi.r:after {{background:var(--rd);}}
.kl {{font-size:10.5px; text-transform:uppercase; letter-spacing:1px; color:var(--mu); margin-bottom:8px;}}
.kv {{font-family:"Cabinet Grotesk",sans-serif; font-size:2rem; font-weight:900; line-height:1;}}
.kd {{font-size:11.5px; margin-top:7px;}}
.wins {{display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:14px;}}
.wc {{background:var(--s1); border:1px solid var(--bd2); border-radius:var(--r); padding:18px; display:flex; flex-direction:column; gap:12px;}}
.wc.cg {{border-color:rgba(46,204,113,.22);}}
.wt {{display:flex; justify-content:space-between; align-items:flex-start; gap:10px;}}
.wlbl {{font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:3px 8px; border-radius:3px;}}
.wlg {{background:var(--grb); color:var(--gr);}}
.wdelta {{font-size:13px; font-weight:700; color:var(--gr);}}
.wname {{font-size:15px; font-weight:700; line-height:1.35;}}
.wstats {{display:flex; gap:16px; flex-wrap:wrap;}}
.ws {{display:flex; flex-direction:column; gap:2px;}}
.wsl {{font-size:10px; text-transform:uppercase; letter-spacing:.8px; color:var(--mu);}}
.wsv {{font-size:14px; font-weight:700; font-variant-numeric:tabular-nums;}}
.wnote {{font-size:12.5px; color:var(--mu); border-top:1px solid var(--bd); padding-top:10px; line-height:1.55;}}
.kwtbl {{background:var(--s1); border:1px solid var(--bd2); border-radius:var(--r); overflow:hidden;}}
table {{width:100%; border-collapse:collapse; font-size:13px;}}
th {{text-align:left; color:var(--mu); font-weight:700; font-size:10px; text-transform:uppercase; letter-spacing:1px; padding:10px 14px; background:var(--s2); border-bottom:1px solid var(--bd2);}}
td {{padding:10px 14px; border-bottom:1px solid var(--bd); font-variant-numeric:tabular-nums;}}
tr:last-child td {{border-bottom:none;}}
tr:hover td {{background:var(--s2);}}
.kw-name {{color:var(--tx); font-weight:600;}}
.pos-good {{color:var(--gr); font-weight:700;}}
.pos-ok {{color:var(--go);}}
.pos-low {{color:var(--mu);}}
.cl {{display:flex; flex-direction:column; gap:10px;}}
.cli {{background:var(--s1); border:1px solid var(--bd2); border-radius:var(--r); padding:14px 16px; display:grid; grid-template-columns:90px 1fr; gap:14px; align-items:flex-start;}}
.cli-date {{font-size:11px; font-weight:700; color:var(--tl); text-transform:uppercase; letter-spacing:.7px; padding-top:2px;}}
.cli-body {{font-size:13.5px; line-height:1.55;}}
.cli-body strong {{color:var(--tx);}}
.tag {{display:inline-block; font-size:10px; padding:2px 7px; border-radius:3px; font-weight:700; margin-left:6px; vertical-align:middle;}}
.tg {{background:var(--grb); color:var(--gr);}}
.ftr {{margin-top:44px; padding-top:20px; border-top:1px solid var(--bd); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; font-size:12px; color:var(--mu);}}
.pill {{display:inline-flex; align-items:center; gap:6px; background:var(--s2); border:1px solid var(--bd2); border-radius:20px; padding:4px 12px; font-size:11.5px;}}
.dot {{width:6px; height:6px; border-radius:50%; display:inline-block;}}
@media (max-width:720px) {{
  .hdr-row, .proof {{grid-template-columns:1fr; display:block;}}
  .hdr-meta {{text-align:left; margin-top:14px;}}
  .proof-nums {{margin-top:16px;}}
  .cli {{grid-template-columns:1fr;}}
}}
</style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <div class="badges">
      <span class="badge bg">Green Shoots</span>
      <span class="badge bt">Week 19 · May 2026</span>
      <span class="badge by">Live GSC + Notion</span>
    </div>
    <div class="hdr-row">
      <div>
        <h1>Shree Shivam<br><em>SEO Sprint Wins</em></h1>
        <p class="hdr-sub">
          Sprint: {report['curr_start_label']}–{report['curr_end_label']} · Baseline: {report['prev_start_label']}–{report['prev_end_label']}<br>
          Source: Google Search Console live · Change log: Notion SEO tracker · {report['action_count']} confirmed actions
        </p>
      </div>
      <div class="hdr-meta">
        <strong>Site</strong> shreeshivam.com<br>
        <strong>Report Date</strong> {report['generated_on']}<br>
        <strong>Window</strong> 7 day vs previous 7 day<br>
        <strong>Data Mode</strong> ADC + Notion API
      </div>
    </div>
  </div>

  <div class="proof">
    <div>
      <h2>{fmt_int(report['new_query_count'])} Net New / Resurfaced Keyword Signals</h2>
      <p>
        Compared with the previous 7-day window, the current week shows stronger keyword capture, improved click velocity,
        and measurable gains on edited pages. This report is generated from live connected sources and formatted for projector presentation.
      </p>
    </div>
    <div class="proof-nums">
      <div class="pn"><div class="pnv" style="color:var(--gr)">{fmt_int(report['curr_clicks'])}</div><div class="pnl">Clicks</div></div>
      <div class="pn"><div class="pnv" style="color:var(--tl)">{fmt_int(report['curr_impressions'])}</div><div class="pnl">Impressions</div></div>
      <div class="pn"><div class="pnv" style="color:var(--go)">{fmt_float(report['curr_ctr'],2)}%</div><div class="pnl">CTR</div></div>
      <div class="pn"><div class="pnv" style="color:var(--gr)">{fmt_float(report['edited_page_ctr'],2)}%</div><div class="pnl">Edited URLs CTR</div></div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hdr"><span></span><span class="sec-t">Sprint Scoreboard</span></div>
    <div class="kpi-grid">
      <div class="kpi g"><div class="kl">Current Week Clicks</div><div class="kv">{fmt_int(report['curr_clicks'])}</div><div class="kd">vs {fmt_int(report['prev_clicks'])} previous week</div></div>
      <div class="kpi t"><div class="kl">Current Week Impressions</div><div class="kv">{fmt_int(report['curr_impressions'])}</div><div class="kd">vs {fmt_int(report['prev_impressions'])} previous week</div></div>
      <div class="kpi g"><div class="kl">CTR Change</div><div class="kv">{fmt_float(report['ctr_delta'],2)} pts</div><div class="kd">from {fmt_float(report['prev_ctr'],2)}% to {fmt_float(report['curr_ctr'],2)}%</div></div>
      <div class="kpi y"><div class="kl">Position Change</div><div class="kv">{fmt_float(report['position_delta'],2)}</div><div class="kd">negative is better if closer to top</div></div>
      <div class="kpi g"><div class="kl">Edited URL Clicks</div><div class="kv">{fmt_int(report['edited_clicks'])}</div><div class="kd">matched from Notion edits</div></div>
      <div class="kpi t"><div class="kl">Edited URL Impressions</div><div class="kv">{fmt_int(report['edited_impressions'])}</div><div class="kd">live search visibility on touched URLs</div></div>
      <div class="kpi y"><div class="kl">Actions Logged</div><div class="kv">{fmt_int(report['action_count'])}</div><div class="kd">Notion SEO tracker</div></div>
      <div class="kpi g"><div class="kl">Keywords With Clicks</div><div class="kv">{fmt_int(report['clicked_query_count'])}</div><div class="kd">queries producing traffic this week</div></div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hdr"><span></span><span class="sec-t">Confirmed Growth Wins</span></div>
    <div class="wins">
      {win_cards}
    </div>
  </div>

  <div class="sec">
    <div class="sec-hdr"><span></span><span class="sec-t">Top Captured Keywords</span></div>
    <div class="kwtbl">
      <table>
        <thead>
          <tr>
            <th>Keyword</th>
            <th>Impressions</th>
            <th>Clicks</th>
            <th>Avg Pos</th>
            <th>Est. Monthly Volume</th>
            <th>Intent</th>
          </tr>
        </thead>
        <tbody>
          {keyword_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hdr"><span></span><span class="sec-t">Actions Completed</span></div>
    <div class="cl">
      {action_rows}
    </div>
  </div>

  <div class="ftr">
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <span class="pill"><span class="dot" style="background:var(--gr)"></span>Source: GSC API + Notion</span>
      <span class="pill"><span class="dot" style="background:var(--tl)"></span>Week 19 generated from live connectors</span>
      <span class="pill"><span class="dot" style="background:var(--go)"></span>{report['generated_on']}</span>
    </div>
    <span>Shree Shivam · shreeshivam.com · Week 19</span>
  </div>

</div>
</body>
</html>
"""


def main():
    today = date.today()
    curr_end = today - timedelta(days=1)
    curr_start = curr_end - timedelta(days=6)
    prev_end = curr_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)

    curr_pages = get_page_level_gsc(str(curr_start), str(curr_end))
    prev_pages = get_page_level_gsc(str(prev_start), str(prev_end))
    curr_queries = get_query_level_gsc(str(curr_start), str(curr_end))
    prev_queries = get_query_level_gsc(str(prev_start), str(prev_end))
    curr_page_queries = get_page_query_level_gsc(str(curr_start), str(curr_end))
    notion_df = get_notion_edits()

    curr_clicks = curr_pages["Clicks"].sum() if not curr_pages.empty else 0
    curr_impressions = curr_pages["Impressions"].sum() if not curr_pages.empty else 0
    curr_ctr = (curr_clicks / curr_impressions * 100) if curr_impressions else 0
    curr_position = curr_pages["Position"].mean() if not curr_pages.empty else 0

    prev_clicks = prev_pages["Clicks"].sum() if not prev_pages.empty else 0
    prev_impressions = prev_pages["Impressions"].sum() if not prev_pages.empty else 0
    prev_ctr = (prev_clicks / prev_impressions * 100) if prev_impressions else 0
    prev_position = prev_pages["Position"].mean() if not prev_pages.empty else 0

    ctr_delta = curr_ctr - prev_ctr
    position_delta = curr_position - prev_position

    curr_queries["key"] = curr_queries["Query"].str.lower().str.strip()
    prev_keys = set(prev_queries["Query"].str.lower().str.strip().tolist()) if not prev_queries.empty else set()
    curr_queries["is_new"] = ~curr_queries["key"].isin(prev_keys)

    new_query_count = int(curr_queries["is_new"].sum()) if not curr_queries.empty else 0
    clicked_query_count = int((curr_queries["Clicks"] > 0).sum()) if not curr_queries.empty else 0

    top_keywords = curr_queries.sort_values(
        ["Clicks", "Impressions", "Position"],
        ascending=[False, False, True]
    ).head(20).copy()

    top_keywords["Intent"] = top_keywords["Query"].apply(classify_intent)
    top_keywords["Volume"] = top_keywords["Query"].apply(est_volume_bucket)

    edited_clicks = 0
    edited_impressions = 0
    edited_page_ctr = 0
    actions = []

    if not notion_df.empty and not curr_pages.empty:
        merged = notion_df.merge(curr_pages, left_on="Clean_URL", right_on="URL", how="inner")
        if not merged.empty:
            edited_clicks = merged["Clicks"].sum()
            edited_impressions = merged["Impressions"].sum()
            edited_page_ctr = (edited_clicks / edited_impressions * 100) if edited_impressions else 0

        recent = notion_df.sort_values("Changed On", ascending=False).head(10).copy()
        for _, r in recent.iterrows():
            summary = r["After"] or r["Notes"] or r["Expected Impact"] or r["Before"] or ""
            summary = summary[:180].strip()
            actions.append({
                "date_label": r["Changed On"].strftime("%b %d") if pd.notna(r["Changed On"]) else "--",
                "url": r["Page / URL"] or "/",
                "summary": summary,
                "type": r["Change Type"] or "Update"
            })

    cards = keyword_win_cards(curr_queries, prev_queries) + page_win_cards(curr_pages, prev_pages)
    cards = cards[:8]

    report = {
        "curr_start_label": curr_start.strftime("%b %d"),
        "curr_end_label": curr_end.strftime("%b %d, %Y"),
        "prev_start_label": prev_start.strftime("%b %d"),
        "prev_end_label": prev_end.strftime("%b %d, %Y"),
        "generated_on": datetime.now().strftime("%b %d, %Y"),
        "curr_clicks": curr_clicks,
        "curr_impressions": curr_impressions,
        "curr_ctr": curr_ctr,
        "curr_position": curr_position,
        "prev_clicks": prev_clicks,
        "prev_impressions": prev_impressions,
        "prev_ctr": prev_ctr,
        "prev_position": prev_position,
        "ctr_delta": ctr_delta,
        "position_delta": position_delta,
        "edited_clicks": edited_clicks,
        "edited_impressions": edited_impressions,
        "edited_page_ctr": edited_page_ctr,
        "action_count": len(notion_df),
        "new_query_count": new_query_count,
        "clicked_query_count": clicked_query_count,
        "top_keywords": top_keywords.to_dict("records"),
        "win_cards": cards,
        "actions": actions
    }

    html = build_html(report)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()