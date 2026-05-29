"""
Blog Performance Monitor
39 articles · after 20 Apr 2026 · GSC analytics + URL Inspection.

Layout: 3 tabs — Article Overview | Keyword Drilldown | URL Inspection.
Tables rendered as native HTML (components.html) for unrestricted
horizontal + vertical scroll without Streamlit container clipping.
"""

import os, sys, math, time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_connectors import get_google_credentials

GSC_PROPERTY = "sc-domain:shreeshivam.com"
BASE_URL     = "https://www.shreeshivam.com"

ARTICLES = [
    ("2026-04-23", "5-elegant-ways-to-style-a-beige-kurti-set"),
    ("2026-04-25", "contrast-kurti-set-trending-2026"),
    ("2026-04-27", "black-thread-work-kurti-designs-2026"),
    ("2026-04-29", "office-wear-kurti-set-styling-2026"),
    ("2026-05-01", "kurti-set-for-wedding-guest-styling-guide"),
    ("2026-05-04", "kurti-set-vs-salwar-suit-difference"),
    ("2026-05-05", "bridal-lehenga-2026-latest-designs-style-guide-for-the-modern-bride"),
    ("2026-05-06", "face-of-shree-shivam-2026-the-stylish-kid-season-3"),
    ("2026-05-07", "wedding-saree-for-bride-the-ultimate-2026-bridal-saree-guide"),
    ("2026-05-12", "the-ready-to-wear-saree-guide-2026-zip-and-go-elegance"),
    ("2026-05-12", "10-stunning-indo-western-dresses-for-2026-weddings-the-ultimate-fusion-guide"),
    ("2026-05-13", "co-ord-set-women-2026-style-guide"),
    ("2026-05-13", "10-best-gowns-for-women-in-2026-the-ultimate-wedding-party-wear-guide"),
    ("2026-05-14", "5-affordable-summer-haul-cotton-kurta-sets-under-2-500-your-ultimate-guide"),
    ("2026-05-14", "10-must-buys-expert-buying-guide-for-affordable-party-sarees-in-raipur-nagpur"),
    ("2026-05-15", "10-most-wanted-simple-back-blouse-designs-to-elevate-your-ethnic-wear-game-in-2026"),
    ("2026-05-15", "office-casual-cotton-sarees"),
    ("2026-05-18", "cotton-kurtis-raipur-nagpur"),
    ("2026-05-18", "party-wear-saree-guide-2026"),
    ("2026-05-19", "modern-salwar-suit-styling-guide-2026"),
    ("2026-05-19", "dupatta-guide-raipur-nagpur"),
    ("2026-05-20", "pakistani-suits-guide-2026"),
    ("2026-05-20", "girlish-suit-designs-2026"),
    ("2026-05-21", "suit-sets-styling-guide-2026"),
    ("2026-05-21", "chic-suit-designs-women-2026"),
    ("2026-05-22", "kurta-sets-for-women-2026-trends"),
    ("2026-05-22", "anarkali-kurta-set-guide-2026"),
    ("2026-05-23", "salwar-suit-design-trends-2026"),
    ("2026-05-23", "cotton-suit-prints-and-weaves-2026"),
    ("2026-05-25", "ladies-suit-designs-2026"),
    ("2026-05-25", "kurta-for-women-complete-guide-2026"),
    ("2026-05-26", "ethnic-dresses-for-women-2026"),
    ("2026-05-26", "gown-for-women-wedding-styles-2026"),
    ("2026-05-27", "lehenga-for-women-party-wear-2026"),
    ("2026-05-27", "wedding-guest-guide-outfits-wishes-2026"),
    ("2026-05-28", "anarkali-suit-party-wear-2026"),
    ("2026-05-28", "sleeve-design-for-kurti-2026"),
    ("2026-05-29", "patiala-suit-guide-2026"),
    ("2026-05-29", "kurti-designs-for-women-2026"),
]
ARTICLE_URLS = {f"{BASE_URL}/blogs/blog/{h}": d for d, h in ARTICLES}

# ── Colour helpers ─────────────────────────────────────────────────────────────

_COVERAGE_MAP = {
    "SUBMITTED_AND_INDEXED":         ("Indexed",               "#dcfce7", "#166534"),
    "CRAWLED_CURRENTLY_NOT_INDEXED": ("Crawled, Not Indexed",  "#fef9c3", "#854d0e"),
    "SUBMITTED_AND_NOT_INDEXED":     ("Submitted, Not Indexed","#fef9c3", "#854d0e"),
    "ALTERNATE_PAGE":                ("Alternate/Dup",         "#fef9c3", "#854d0e"),
    "DUPLICATE_WITHOUT_CANONICAL":   ("Duplicate",             "#fef9c3", "#854d0e"),
    "EXCLUDED_BY_ROBOTS_TXT":        ("Blocked robots.txt",    "#fee2e2", "#991b1b"),
    "SOFT_404":                      ("Soft 404",              "#fee2e2", "#991b1b"),
    "PAGE_WITH_REDIRECT":            ("Redirect",              "#fee2e2", "#991b1b"),
    "NOT_FOUND":                     ("Not Found",             "#fee2e2", "#991b1b"),
}
def _cov_label(raw): return _COVERAGE_MAP.get(raw, (raw, "#e5e7eb", "#374151"))[0]
def _cov_color(label):
    for _, (lbl, bg, fg) in _COVERAGE_MAP.items():
        if lbl == label: return bg, fg
    if label == "Has data":  return "#dcfce7", "#166534"
    if label == "Pending":   return "#fef9c3", "#854d0e"
    if label == "No data":   return "#fee2e2", "#991b1b"
    return "#f3f4f6", "#374151"


_BAND_ORDER = ["Top 3", "4–10", "11–20", "21–50", "51+"]

def _pos_band(pos):
    if pos <=  3: return "Top 3"
    if pos <= 10: return "4–10"
    if pos <= 20: return "11–20"
    if pos <= 50: return "21–50"
    return "51+"


# ── HTML table renderer ────────────────────────────────────────────────────────

def _th(text, align="left", extra=""):
    return (f'<th style="padding:8px 14px;text-align:{align};white-space:nowrap;'
            f'border-bottom:2px solid #d1d5db;background:#f1f5f9;color:#111827;'
            f'position:sticky;top:0;z-index:2;font-weight:600;{extra}">{text}</th>')

def _td(text, align="left", bg="#ffffff", fg="#111827", bold=False, nowrap=False, border_left=""):
    s = (f"padding:6px 14px;text-align:{align};"
         f"background:{bg};color:{fg};border-bottom:1px solid #f3f4f6;")
    if bold:         s += "font-weight:600;"
    if nowrap:       s += "white-space:nowrap;"
    if border_left:  s += f"border-left:4px solid {border_left};"
    return f'<td style="{s}">{text}</td>'

def _html_wrap(inner_html, height=700, min_width=1200):
    # Full HTML doc with explicit white background — immune to Streamlit dark theme.
    # min_width wider than the iframe container forces the horizontal scrollbar to appear.
    return f"""<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #ffffff; color: #111827;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          font-size: 13px; line-height: 1.45; }}
  .wrap {{ overflow-x: scroll; overflow-y: auto;
           max-height: {height}px; width: 100%;
           border: 1px solid #e5e7eb; border-radius: 6px; }}
  table {{ border-collapse: collapse; min-width: {min_width}px; width: max-content; }}
  tbody tr:hover td {{ background: #f8fafc !important; }}
</style>
</head>
<body>
<div class="wrap">
  <table>{inner_html}</table>
</div>
</body>
</html>"""


def _overview_html(df):
    headers = ["#", "Published", "Days", "Handle", "GSC Status",
               "Clicks", "Impressions", "Avg Pos", "Best Pos",
               "# KWs", "Top 3", "Top 10", "Top Keyword", "Top KW Pos",
               "Index Status", "Last Crawled"]
    aligns  = ["right","left","right","left","left",
               "right","right","right","right",
               "right","right","right","left","right",
               "left","left"]
    head = "<thead><tr>" + "".join(_th(h, a) for h, a in zip(headers, aligns)) + "</tr></thead>"

    # Accent colours for GSC status (border-left only — cell stays white)
    _ACCENT = {"Has data": "#16a34a", "Pending": "#d97706", "No data": "#dc2626"}

    rows = ""
    for i, (_, r) in enumerate(df.iterrows(), 1):
        accent      = _ACCENT.get(r["GSC Status"], "#9ca3af")
        gsc_bg, gsc_fg = _cov_color(r["GSC Status"])
        idx_bg, idx_fg = _cov_color(r.get("Index Status", "—"))

        def fpos(v):
            try:
                f = float(v)
                return "—" if math.isnan(f) else f"{f:.1f}"
            except: return "—"

        cells = [
            _td(str(i), "right"),
            # First data cell carries the accent border so the row feels colour-coded
            _td(r["Published"], nowrap=True, border_left=accent),
            _td(str(r["Days Live"]), "right"),
            _td(f'<a href="{BASE_URL}/blogs/blog/{r["Handle"]}" target="_blank" '
                f'style="color:#2563eb;text-decoration:none;font-size:12px">{r["Handle"]}</a>'),
            # GSC Status pill — coloured bg on this cell only
            _td(f'<span style="background:{gsc_bg};color:{gsc_fg};padding:2px 8px;'
                f'border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap">'
                f'{r["GSC Status"]}</span>', "left"),
            _td(f'{int(r["Clicks"]):,}',      "right"),
            _td(f'{int(r["Impressions"]):,}', "right", bold=r["Impressions"] > 500),
            _td(fpos(r["Avg Pos"]),  "right"),
            _td(fpos(r["Best Pos"]), "right", bold=True,
                fg="#16a34a" if (r["Best Pos"] or 999) <= 10 else "#111827"),
            _td(str(int(r["# Keywords"])),  "right"),
            _td(str(int(r["Top 3"])),  "right",
                bold=r["Top 3"]>0, fg="#16a34a" if r["Top 3"]>0 else "#6b7280"),
            _td(str(int(r["Top 10"])), "right",
                bold=r["Top 10"]>0, fg="#0891b2" if r["Top 10"]>0 else "#6b7280"),
            _td(f'<span style="font-size:12px">{r["Top Keyword"]}</span>'),
            _td(fpos(r["Top KW Pos"]), "right"),
            _td(f'<span style="background:{idx_bg};color:{idx_fg};padding:2px 8px;'
                f'border-radius:4px;font-size:11px;white-space:nowrap">'
                f'{r.get("Index Status","—")}</span>', "left"),
            _td(str(r.get("Last Crawled", "—")), nowrap=True),
        ]
        rows += "<tr>" + "".join(cells) + "</tr>"

    tbl_h = min(len(df) * 38 + 55, 820)
    return _html_wrap(
        "<thead>" + head[8:-9] + "</thead><tbody>" + rows + "</tbody>",
        height=tbl_h, min_width=1500,
    )


def _keyword_html(df):
    head = "<thead><tr>" + "".join([
        _th("#",           "right"),
        _th("Band",        "left"),
        _th("Keyword",     "left",  "min-width:300px"),
        _th("Position",    "right"),
        _th("Impressions", "right"),
        _th("Clicks",      "right"),
        _th("CTR %",       "right"),
    ]) + "</tr></thead>"

    # Border-left accent per band, readable pill for band label
    _BAND_BORDER = {
        "Top 3":  "#16a34a",
        "4–10":   "#0891b2",
        "11–20":  "#d97706",
        "21–50":  "#ea580c",
        "51+":    "#9ca3af",
    }
    _BAND_PILL = {
        "Top 3":  ("#dcfce7", "#14532d"),
        "4–10":   ("#cffafe", "#164e63"),
        "11–20":  ("#fef9c3", "#713f12"),
        "21–50":  ("#ffedd5", "#7c2d12"),
        "51+":    ("#f3f4f6", "#374151"),
    }
    # Position cell colouring
    def pos_style(p):
        if p <=  3: return "#dcfce7", "#14532d"
        if p <= 10: return "#cffafe", "#164e63"
        if p <= 20: return "#fef9c3", "#713f12"
        if p <= 50: return "#ffedd5", "#7c2d12"
        return "#ffffff", "#374151"

    rows = ""
    for i, (_, r) in enumerate(df.iterrows(), 1):
        band   = r["Band"]
        accent = _BAND_BORDER.get(band, "#9ca3af")
        pb, pf = _BAND_PILL.get(band, ("#f3f4f6","#374151"))
        vb, vf = pos_style(r["Position"])
        rows += "<tr>"
        rows += _td(str(i), "right")
        rows += _td(
            f'<span style="background:{pb};color:{pf};padding:2px 8px;'
            f'border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap">{band}</span>',
            border_left=accent,
        )
        kw_raw  = str(r["Keyword"])
        kw_safe = kw_raw.replace('"', '&quot;').replace("'", "&#39;")
        kw_disp = (kw_raw[:80] + "…") if len(kw_raw) > 80 else kw_raw
        rows += (f'<td style="padding:6px 14px;background:#ffffff;color:#111827;'
                 f'border-bottom:1px solid #f3f4f6;max-width:340px;'
                 f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" '
                 f'title="{kw_safe}">{kw_disp}</td>')
        rows += _td(f'{r["Position"]:.1f}', "right", bg=vb, fg=vf, bold=True)
        rows += _td(f'{int(r["Impressions"]):,}', "right")
        rows += _td(f'{int(r["Clicks"]):,}',      "right")
        rows += _td(f'{r["CTR %"]:.2f}%',         "right")
        rows += "</tr>"

    tbl_h = min(len(df) * 36 + 55, 900)
    return _html_wrap(
        "<thead>" + head[8:-9] + "</thead><tbody>" + rows + "</tbody>",
        height=tbl_h, min_width=900,
    )


def _inspection_html(rows_data):
    head = "<thead><tr>" + "".join([
        _th("Published"),
        _th("Handle", "left", "min-width:320px"),
        _th("Index Status"),
        _th("Last Crawled"),
        _th("Crawled As"),
        _th("Indexing State"),
        _th("Robots.txt"),
    ]) + "</tr></thead>"

    _INSP_ACCENT = {
        "Indexed":               "#16a34a",
        "Crawled, Not Indexed":  "#d97706",
        "Submitted, Not Indexed":"#d97706",
        "Not Found":             "#dc2626",
        "Soft 404":              "#dc2626",
        "Blocked robots.txt":    "#dc2626",
    }

    rows = ""
    for r in rows_data:
        bg, fg = _cov_color(r["Index Status"])
        accent = _INSP_ACCENT.get(r["Index Status"], "#9ca3af")
        rows += "<tr>"
        rows += _td(r["Published"], nowrap=True, border_left=accent)
        rows += _td(f'<a href="{BASE_URL}/blogs/blog/{r["Handle"]}" target="_blank" '
                    f'style="color:#2563eb;text-decoration:none;font-size:12px">{r["Handle"]}</a>')
        rows += _td(
            f'<span style="background:{bg};color:{fg};padding:2px 8px;'
            f'border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap">'
            f'{r["Index Status"]}</span>', "left")
        rows += _td(r["Last Crawled"],   nowrap=True)
        rows += _td(r["Crawled As"],     nowrap=True)
        rows += _td(r["Indexing State"], nowrap=True)
        rows += _td(r["Robots.txt"],     nowrap=True)
        rows += "</tr>"

    tbl_h = min(len(rows_data) * 38 + 55, 820)
    return _html_wrap(
        "<thead>" + head[8:-9] + "</thead><tbody>" + rows + "</tbody>",
        height=tbl_h, min_width=1100,
    )


# ── GSC data fetchers ──────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_article_meta(url: str) -> dict:
    """Fetch title, meta title and meta description from the live URL."""
    import re, html as html_mod
    try:
        import requests as _req
        resp = _req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        src  = resp.text

        def _first(pattern, flags=re.IGNORECASE | re.DOTALL):
            m = re.search(pattern, src, flags)
            return html_mod.unescape(m.group(1).strip()) if m else ""

        page_title  = _first(r"<title[^>]*>(.*?)</title>")
        meta_title  = (
            _first(r'<meta\s+name=["\']title["\']\s+content=["\'](.*?)["\']')
            or _first(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']title["\']')
            or _first(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']')
        )
        meta_desc   = (
            _first(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']')
            or _first(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']')
        )
        return {
            "page_title":  page_title,
            "meta_title":  meta_title,
            "meta_desc":   meta_desc,
        }
    except Exception as e:
        return {"page_title": "", "meta_title": "", "meta_desc": f"Error: {e}"}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_gsc_data(days=90):
    try:
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        if not creds: return pd.DataFrame()
        svc   = build("searchconsole", "v1", credentials=creds)
        end   = datetime.today()
        start = end - timedelta(days=days)
        body  = {
            "startDate":  start.strftime("%Y-%m-%d"),
            "endDate":    end.strftime("%Y-%m-%d"),
            "dimensions": ["page", "query"],
            "dimensionFilterGroups": [{"filters": [{
                "dimension": "page", "operator": "contains",
                "expression": "/blogs/blog/",
            }]}],
            "rowLimit": 25000,
        }
        resp = svc.searchanalytics().query(siteUrl=GSC_PROPERTY, body=body).execute()
        rows = resp.get("rows", [])
        if not rows: return pd.DataFrame()
        return pd.DataFrame([{
            "url": r["keys"][0], "keyword": r["keys"][1],
            "clicks": int(r["clicks"]), "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"]*100, 2), "position": round(r["position"], 1),
        } for r in rows])
    except Exception as e:
        st.error(f"GSC error: {e}")
        return pd.DataFrame()


def run_url_inspection(urls):
    from googleapiclient.discovery import build
    creds = get_google_credentials()
    if not creds: return {}
    svc, results = build("searchconsole", "v1", credentials=creds), {}
    bar = st.progress(0, text="Running URL Inspection…")
    for i, url in enumerate(urls):
        try:
            resp = svc.urlInspection().index().inspect(body={
                "inspectionUrl": url, "siteUrl": GSC_PROPERTY,
            }).execute()
            isr = resp.get("inspectionResult", {}).get("indexStatusResult", {})
            raw = isr.get("coverageState", "UNKNOWN")
            results[url] = {
                "coverage": _cov_label(raw), "raw_coverage": raw,
                "indexing_state": isr.get("indexingState", "—"),
                "last_crawl":     (isr.get("lastCrawlTime") or "")[:10],
                "crawled_as":     isr.get("crawledAs", "—"),
                "robots_txt":     isr.get("robotsTxtState", "—"),
            }
        except Exception as e:
            results[url] = {"coverage": "Error", "raw_coverage": "ERROR",
                            "indexing_state": str(e)[:80],
                            "last_crawl": "—", "crawled_as": "—", "robots_txt": "—"}
        bar.progress((i+1)/len(urls), text=f"Inspecting {i+1}/{len(urls)}: …{url[-40:]}")
        time.sleep(0.5)
    bar.empty()
    return results


# ── Summary builder ───────────────────────────────────────────────────────────

def build_summary(gsc_df, inspection):
    today = datetime.today().date()
    rows  = []
    for pub_date, handle in ARTICLES:
        url      = f"{BASE_URL}/blogs/blog/{handle}"
        age_days = (today - datetime.strptime(pub_date, "%Y-%m-%d").date()).days
        if not gsc_df.empty and url in gsc_df["url"].values:
            art = gsc_df[gsc_df["url"] == url]
            top = art.sort_values("impressions", ascending=False).iloc[0]
            row = {
                "Published": pub_date, "Days Live": age_days, "Handle": handle,
                "GSC Status":  "Has data",
                "Clicks":      int(art["clicks"].sum()),
                "Impressions": int(art["impressions"].sum()),
                "Avg Pos":     round(art["position"].mean(), 1),
                "Best Pos":    round(art["position"].min(), 1),
                "# Keywords":  len(art),
                "Top 3":       int((art["position"] <= 3).sum()),
                "Top 10":      int((art["position"] <= 10).sum()),
                "Top Keyword": top["keyword"],
                "Top KW Pos":  top["position"],
            }
        else:
            row = {
                "Published": pub_date, "Days Live": age_days, "Handle": handle,
                "GSC Status":  "Pending" if age_days <= 28 else "No data",
                "Clicks": 0, "Impressions": 0, "Avg Pos": None, "Best Pos": None,
                "# Keywords": 0, "Top 3": 0, "Top 10": 0,
                "Top Keyword": "—", "Top KW Pos": None,
            }
        insp = inspection.get(url, {})
        row.update({
            "Index Status":   insp.get("coverage", "—"),
            "Last Crawled":   insp.get("last_crawl", "—"),
            "Crawled As":     insp.get("crawled_as", "—"),
            "Indexing State": insp.get("indexing_state", "—"),
        })
        rows.append(row)
    return pd.DataFrame(rows)


# ── Main render ───────────────────────────────────────────────────────────────

def render(master_df, notion_df):
    st.title("Blog Performance Monitor")
    st.caption(
        f"39 articles · published after 20 Apr 2026 · "
        f"GSC 90-day analytics + URL Inspection · {datetime.today().strftime('%d %b %Y')}"
    )

    if "inspection_results" not in st.session_state:
        st.session_state["inspection_results"] = {}

    with st.spinner("Loading GSC analytics…"):
        gsc_df = fetch_gsc_data(days=90)
    summary_df = build_summary(gsc_df, st.session_state["inspection_results"])
    inspected  = len(st.session_state["inspection_results"])

    # ── KPI strip ─────────────────────────────────────────────────────────────
    has_data = (summary_df["GSC Status"] == "Has data").sum()
    pending  = (summary_df["GSC Status"] == "Pending").sum()
    no_data  = (summary_df["GSC Status"] == "No data").sum()
    conf_idx = sum(1 for v in st.session_state["inspection_results"].values()
                   if v.get("raw_coverage") == "SUBMITTED_AND_INDEXED")

    k = st.columns(8)
    k[0].metric("Articles",     39)
    k[1].metric("Has GSC Data", has_data)
    k[2].metric("Pending",      pending)
    k[3].metric("No Data",      no_data)
    k[4].metric("Confirmed Idx",conf_idx if inspected else "—")
    k[5].metric("Clicks",       f"{summary_df['Clicks'].sum():,}")
    k[6].metric("Impressions",  f"{summary_df['Impressions'].sum():,}")
    k[7].metric("Keywords",     f"{summary_df['# Keywords'].sum():,}")

    st.divider()

    tab_ov, tab_kw, tab_insp = st.tabs([
        "Article Overview", "Keyword Drilldown", "URL Inspection"
    ])

    # ═══════════════════════════════════════════════════════════
    # TAB 1 — Article Overview
    # ═══════════════════════════════════════════════════════════
    with tab_ov:
        cf, cs = st.columns([3, 2])
        with cf:
            sf = st.multiselect("Filter status", ["Has data","Pending","No data"],
                                default=["Has data","Pending","No data"], key="ov_sf")
        with cs:
            sb = st.selectbox("Sort by",
                              ["Published (newest)","Impressions","Clicks",
                               "Best Pos","Avg Pos","# Keywords","Top 3","Top 10"],
                              key="ov_sb")

        disp = summary_df[summary_df["GSC Status"].isin(sf)].copy()
        if sb == "Published (newest)":    disp = disp.sort_values("Published", ascending=False)
        elif sb in ("Best Pos","Avg Pos"):disp = disp.sort_values(sb, ascending=True,  na_position="last")
        else:                             disp = disp.sort_values(sb, ascending=False)

        html_ov = _overview_html(disp)
        # iframe height = table height + 30px padding
        tbl_h_ov = min(len(disp)*38+55, 820)
        components.html(html_ov, height=tbl_h_ov + 30, scrolling=True)

        csv_ov = disp.drop(columns=["Crawled As","Indexing State"], errors="ignore")\
                     .to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv_ov, "blog_overview.csv", "text/csv", key="dl_ov")

    # ═══════════════════════════════════════════════════════════
    # TAB 2 — Keyword Drilldown
    # ═══════════════════════════════════════════════════════════
    with tab_kw:
        # Article selector — richest articles first
        opts = []
        for _, r in summary_df.sort_values("Impressions", ascending=False).iterrows():
            best = f"{r['Best Pos']:.1f}" if r["Best Pos"] is not None else "—"
            opts.append((
                f"{r['Handle']}  ·  {r['Impressions']:,} impr · "
                f"{r['# Keywords']} kws · best #{best}",
                r["Handle"],
            ))

        sel_label  = st.selectbox("Select article to inspect keywords",
                                  [o[0] for o in opts], key="kw_sel")
        sel_handle = next(h for lbl, h in opts if lbl == sel_label)
        sel_url    = f"{BASE_URL}/blogs/blog/{sel_handle}"
        pub_row    = summary_df[summary_df["Handle"] == sel_handle].iloc[0]

        # Meta bar
        insp_v = st.session_state["inspection_results"].get(sel_url, {})
        meta   = [
            f"**Published:** {pub_row['Published']}",
            f"**Days live:** {pub_row['Days Live']}",
            f"**GSC:** {pub_row['GSC Status']}",
        ]
        if insp_v:
            meta += [f"**Index:** {insp_v.get('coverage','—')}",
                     f"**Crawled:** {insp_v.get('last_crawl','—')}"]
        meta.append(f"[Open ↗]({sel_url})")
        st.markdown("  &nbsp;|&nbsp;  ".join(meta))

        st.divider()

        if not gsc_df.empty and sel_url in gsc_df["url"].values:
            art = gsc_df[gsc_df["url"] == sel_url].copy()
            art["Band"] = art["position"].apply(_pos_band)

            # ── Page SEO meta ──────────────────────────────────────────────
            with st.spinner("Fetching page meta…"):
                meta = fetch_article_meta(sel_url)

            pg_title   = meta["page_title"]  or "—"
            mt_title   = meta["meta_title"]  or "—"
            mt_desc    = meta["meta_desc"]   or "—"

            # Character count helpers
            def _clen(s, lo, hi):
                n = len(s)
                colour = "#16a34a" if lo <= n <= hi else "#dc2626"
                return f'<span style="color:{colour};font-size:11px">({n} chars)</span>'

            st.markdown("**Page SEO meta**")
            components.html(f"""<!DOCTYPE html>
<html><head><style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        background:#ffffff;color:#111827;margin:0;padding:8px 0;font-size:13px}}
  .row{{display:flex;gap:8px;align-items:baseline;margin-bottom:10px;
        border-left:3px solid #e5e7eb;padding-left:10px}}
  .lbl{{font-weight:600;white-space:nowrap;min-width:130px;color:#374151}}
  .val{{color:#111827;line-height:1.5;word-break:break-word}}
  .cnt{{font-size:11px;margin-left:6px;white-space:nowrap}}
  .ok{{color:#16a34a}}.bad{{color:#dc2626}}
</style></head><body>
  <div class="row">
    <span class="lbl">Page &lt;title&gt;</span>
    <span class="val">{pg_title}</span>
    <span class="cnt {'ok' if 50<=len(pg_title)<=60 else 'bad'}"
    >({len(pg_title)} chars · ideal 50–60)</span>
  </div>
  <div class="row">
    <span class="lbl">Meta title</span>
    <span class="val">{mt_title}</span>
    <span class="cnt {'ok' if 50<=len(mt_title)<=60 else 'bad'}"
    >({len(mt_title)} chars · ideal 50–60)</span>
  </div>
  <div class="row">
    <span class="lbl">Meta description</span>
    <span class="val">{mt_desc}</span>
    <span class="cnt {'ok' if 120<=len(mt_desc)<=160 else 'bad'}"
    >({len(mt_desc)} chars · ideal 120–160)</span>
  </div>
</body></html>""", height=130, scrolling=False)

            st.divider()

            # Position band KPIs
            st.markdown("**Position bands**")
            bc = st.columns(5)
            for i, band in enumerate(_BAND_ORDER):
                sub  = art[art["Band"] == band]
                cnt  = len(sub)
                impr = int(sub["impressions"].sum())
                clk  = int(sub["clicks"].sum())
                bc[i].metric(band, cnt, f"{impr:,} impr · {clk} clk")

            st.divider()

            # Filters
            fa, fb, fc = st.columns([2, 2, 2])
            with fa:
                band_f = st.multiselect("Position band", _BAND_ORDER,
                                        default=_BAND_ORDER, key="kw_band")
            with fb:
                kw_q   = st.text_input("Search keyword", key="kw_q",
                                       placeholder="filter by text…")
            with fc:
                kw_sort= st.selectbox("Sort by",
                                      ["Impressions","Clicks","Position (best)","CTR %"],
                                      key="kw_sort")

            art_f = art[art["Band"].isin(band_f)].copy()
            if kw_q:
                art_f = art_f[art_f["keyword"].str.contains(kw_q, case=False, na=False)]
            if kw_sort == "Position (best)": art_f = art_f.sort_values("position")
            elif kw_sort == "CTR %":         art_f = art_f.sort_values("ctr", ascending=False)
            elif kw_sort == "Clicks":        art_f = art_f.sort_values("clicks", ascending=False)
            else:                            art_f = art_f.sort_values("impressions", ascending=False)

            # Mini KPIs
            mk = st.columns(5)
            mk[0].metric("Keywords shown",  len(art_f))
            mk[1].metric("Impressions",     f"{int(art_f['impressions'].sum()):,}")
            mk[2].metric("Clicks",          f"{int(art_f['clicks'].sum()):,}")
            mk[3].metric("Avg position",    f"{art_f['position'].mean():.1f}" if len(art_f) else "—")
            mk[4].metric("Best position",   f"{art_f['position'].min():.1f}"  if len(art_f) else "—")

            # Full keyword table — HTML, unrestricted scroll
            kw_display = art_f.rename(columns={
                "keyword":"Keyword","clicks":"Clicks",
                "impressions":"Impressions","ctr":"CTR %","position":"Position",
            })
            html_kw = _keyword_html(kw_display)
            kw_h    = min(len(art_f)*36+55, 900)
            components.html(html_kw, height=kw_h + 30, scrolling=True)

            csv_kw = art_f.drop(columns=["url","Band"]).rename(columns={
                "keyword":"Keyword","clicks":"Clicks","impressions":"Impressions",
                "ctr":"CTR %","position":"Position",
            }).to_csv(index=False).encode("utf-8")
            st.download_button("Download keywords CSV", csv_kw,
                               f"{sel_handle}_keywords.csv", "text/csv", key="dl_kw")

        else:
            st.info(
                f"No GSC data yet — published {pub_row['Days Live']}d ago. "
                + ("Still indexing — check back in a few days." if pub_row["Days Live"]<=28
                   else "Run URL Inspection (tab 3) to diagnose.")
            )

    # ═══════════════════════════════════════════════════════════
    # TAB 3 — URL Inspection
    # ═══════════════════════════════════════════════════════════
    with tab_insp:
        st.markdown(
            "Calls **GSC URL Inspection API** per article — confirms real index "
            "status vs. inferring from impressions. 39 calls · ~20 sec · 2,000 req/day quota."
        )
        b1, b2, b3 = st.columns([2, 2, 4])
        with b1:
            if st.button("Run inspection — all 39", type="primary", key="insp_run"):
                urls = [f"{BASE_URL}/blogs/blog/{h}" for _, h in ARTICLES]
                st.session_state["inspection_results"] = run_url_inspection(urls)
                st.rerun()
        with b2:
            if st.button("Clear", key="insp_clr"):
                st.session_state["inspection_results"] = {}
                st.rerun()
        with b3:
            if inspected:
                conf = sum(1 for v in st.session_state["inspection_results"].values()
                           if v.get("raw_coverage") == "SUBMITTED_AND_INDEXED")
                st.info(f"{inspected}/39 inspected · {conf} confirmed indexed")

        if st.session_state["inspection_results"]:
            insp_rows = []
            for pub_date, handle in ARTICLES:
                url = f"{BASE_URL}/blogs/blog/{handle}"
                v   = st.session_state["inspection_results"].get(url, {})
                insp_rows.append({
                    "Published":      pub_date,
                    "Handle":         handle,
                    "Index Status":   v.get("coverage",       "—"),
                    "Last Crawled":   v.get("last_crawl",     "—"),
                    "Crawled As":     v.get("crawled_as",     "—"),
                    "Indexing State": v.get("indexing_state", "—"),
                    "Robots.txt":     v.get("robots_txt",     "—"),
                })
            insp_h = min(len(insp_rows)*38+55, 820)
            components.html(_inspection_html(insp_rows), height=insp_h+30, scrolling=True)

            insp_csv = pd.DataFrame(insp_rows).to_csv(index=False).encode("utf-8")
            st.download_button("Download inspection CSV", insp_csv,
                               "url_inspection.csv", "text/csv", key="dl_insp")
        else:
            st.caption("No results yet — click Run inspection above.")
