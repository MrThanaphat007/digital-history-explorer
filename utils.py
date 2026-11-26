"""Shared helpers: year formatting, eras, editorial theme (light/dark), Plotly style, base map."""
import html
import folium
import streamlit as st

YEAR_MIN, YEAR_MAX = -3200, 2000


def fmt_year(y) -> str:
    y = int(y)
    return f"{abs(y)} BCE" if y < 0 else f"{y} CE"


def era_of(y) -> str:
    """Conventional (Western-centred) periodisation, used only for filtering."""
    y = int(y)
    if y < 500:
        return "Ancient (before 500 CE)"
    if y < 1500:
        return "Medieval (500-1500)"
    if y < 1800:
        return "Early Modern (1500-1800)"
    return "Modern (1800+)"


ERAS = ["Ancient (before 500 CE)", "Medieval (500-1500)", "Early Modern (1500-1800)", "Modern (1800+)"]
ERA_RANGES = {"Custom": None, "Ancient": (-3200, 499), "Medieval": (500, 1499),
              "Early Modern": (1500, 1799), "Modern": (1800, 2000)}

CERT_LABEL = {"secure": "date secure", "approximate": "date approximate", "traditional": "traditional date"}


def cert_badge(c) -> str:
    """Small label showing how certain a date is (blank when unknown)."""
    return f"<span class='badge {c}'>{CERT_LABEL.get(c, c)}</span>" if isinstance(c, str) and c else ""


def src_link(source, url) -> str:
    """Source name, linked when a verified https URL is stored in the data."""
    s = html.escape(str(source))
    if isinstance(url, str) and url.startswith("https://"):
        return f"<a href='{html.escape(url)}' target='_blank' rel='noopener'>{s} ↗</a>"
    return s


def year_ticks(years):
    """Tick labels that show BCE/CE instead of negative numbers."""
    lo, hi = min(years), max(years)
    step = max(100, int((hi - lo) / 8 // 100 * 100) or 100)
    vals = list(range(int(lo // step * step), int(hi) + step, step))
    return vals, [fmt_year(v) for v in vals]


def palette(dark: bool) -> dict:
    """Editorial palette: ivory, charcoal, olive, terracotta, soft grey."""
    return ({"bg": "#1d1f1c", "panel": "#262823", "text": "#ece8dd", "muted": "#a3a687",
             "accent": "#d68e73", "line": "#3a3d37", "map": "#262823"} if dark else
            {"bg": "#F3F0E8", "panel": "#FAF8F2", "text": "#252724", "muted": "#777A61",
             "accent": "#A6644D", "line": "#D5D1C7", "map": "#E8E4D6"})


def apply_theme(dark: bool) -> dict:
    """Inject CSS: editorial typography, light/dark colours, flat controls, responsive layout."""
    c = palette(dark)
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'DM Sans', sans-serif; }}
h1, h2, h3, h4 {{ font-family: 'Libre Baskerville', Georgia, serif !important; font-weight: 400 !important; color: {c['text']} !important; }}
h1 {{ letter-spacing: -.01em; }}
.stApp {{ background: {c['bg']}; color: {c['text']}; }}
.stApp p, .stApp label, .stApp span, .stApp li, .stApp div[data-testid="stMarkdownContainer"] {{ color: {c['text']}; }}
.stApp a {{ color: {c['accent']}; }}
section[data-testid="stSidebar"] {{ background: {c['bg']}; border-right: 1px solid {c['text']}; }}
[data-testid="stHeader"] {{ background: transparent; }}
div[data-testid="stMetric"] {{ background: transparent; border-top: 1px solid {c['text']}; padding: 10px 0 0; }}
div[data-testid="stMetricLabel"] p {{ font-family: 'IBM Plex Mono', monospace; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; color: {c['muted']}; }}
div[data-testid="stMetricValue"] {{ color: {c['accent']}; font-family: 'Libre Baskerville', serif; }}
div[data-testid="stExpander"], div[data-testid="stForm"] {{ background: transparent; border: 1px solid {c['line']}; border-radius: 0; }}
.stButton > button, .stDownloadButton > button {{ border-radius: 0; border: 1px solid {c['text']}; background: transparent; color: {c['text']}; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ background: {c['text']}; color: {c['bg']}; border-color: {c['text']}; }}
button[data-baseweb="tab"] {{ font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; font-size: .78rem; letter-spacing: .05em; }}
.card {{ background: transparent; border-top: 1px solid {c['text']}; border-bottom: 1px solid {c['line']}; padding: 14px 4px 16px; margin-bottom: 14px; }}
.card h3, .card h4 {{ margin: 4px 0 6px; }}
.card .meta, .meta {{ font-family: 'IBM Plex Mono', monospace; color: {c['muted']}; font-size: .76rem; letter-spacing: .03em; }}
.hero {{ border-bottom: 1px solid {c['text']}; padding-bottom: 10px; margin-bottom: 20px; }}
.small-note {{ font-family: 'IBM Plex Mono', monospace; color: {c['muted']}; font-size: .78rem; }}
.badge {{ font-family: 'IBM Plex Mono', monospace; font-size: .68rem; border: 1px solid {c['muted']}; color: {c['muted']}; padding: 0 6px; margin-left: 6px; }}
.badge.approximate, .badge.traditional {{ border-style: dashed; color: {c['accent']}; border-color: {c['accent']}; }}
@media (max-width: 768px) {{
  .block-container {{ padding: 1rem .8rem !important; }}
  h1 {{ font-size: 1.5rem !important; }}
}}
</style>""", unsafe_allow_html=True)
    return c


def style_fig(fig, dark: bool, height: int = 420):
    """Apply a consistent Plotly look that follows the theme."""
    c = palette(dark)
    fig.update_layout(template="plotly_dark" if dark else "plotly_white", height=height,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      colorway=["#A6644D", "#777A61", "#C2A66B", "#6E7260", "#9C7A8C", "#B8864B"],
                      font=dict(family="DM Sans", color=c["text"]), margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def base_map(location, zoom, dark: bool, modern: bool = False) -> folium.Map:
    """Paper-coloured atlas canvas (no modern basemap) so historical borders stand alone.
    modern=True adds OpenStreetMap underneath (inverted in dark mode via a CSS filter,
    injected into the map itself because maps render inside an iframe)."""
    m = folium.Map(location=location, zoom_start=zoom, tiles="OpenStreetMap" if modern else None,
                   control_scale=True)
    bg = palette(dark)["map"]
    css = f".leaflet-container{{background:{bg} !important}}"
    if modern and dark:
        css += ".leaflet-tile-pane{filter:invert(1) hue-rotate(180deg) brightness(.85) contrast(.9);}"
    m.get_root().header.add_child(folium.Element(f"<style>{css}</style>"))
    return m
