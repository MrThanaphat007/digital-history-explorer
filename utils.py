"""Shared helpers: year formatting, eras, theme (light/dark) and Plotly styling."""
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


def year_ticks(years):
    """Tick labels that show BCE/CE instead of negative numbers."""
    lo, hi = min(years), max(years)
    step = max(100, int((hi - lo) / 8 // 100 * 100) or 100)
    vals = list(range(int(lo // step * step), int(hi) + step, step))
    return vals, [fmt_year(v) for v in vals]


def palette(dark: bool) -> dict:
    return ({"bg": "#14171c", "panel": "#1d2229", "text": "#e9e4d8", "muted": "#9aa3ad",
             "accent": "#d4b06a", "line": "#2b323b"} if dark else
            {"bg": "#f6f1e7", "panel": "#fffdf8", "text": "#2a2420", "muted": "#6d635a",
             "accent": "#7a1f2b", "line": "#e0d6c3"})


def apply_theme(dark: bool) -> dict:
    """Inject CSS for typography, light/dark colours and responsive layout."""
    c = palette(dark)
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; }}
h1, h2, h3, h4 {{ font-family: 'Libre Baskerville', Georgia, serif !important; color: {c['accent']} !important; letter-spacing: .2px; }}
.stApp {{ background: {c['bg']}; color: {c['text']}; }}
.stApp p, .stApp label, .stApp span, .stApp li, .stApp div[data-testid="stMarkdownContainer"] {{ color: {c['text']}; }}
section[data-testid="stSidebar"] {{ background: {c['panel']}; border-right: 1px solid {c['line']}; }}
[data-testid="stHeader"] {{ background: transparent; }}
div[data-testid="stMetric"] {{ background: {c['panel']}; border: 1px solid {c['line']}; border-left: 4px solid {c['accent']};
    padding: 12px 16px; border-radius: 6px; }}
div[data-testid="stMetricValue"] {{ color: {c['accent']}; font-family: 'Libre Baskerville', serif; }}
div[data-testid="stExpander"], div[data-testid="stForm"] {{ background: {c['panel']}; border: 1px solid {c['line']}; border-radius: 6px; }}
.card {{ background: {c['panel']}; border: 1px solid {c['line']}; border-left: 4px solid {c['accent']};
    border-radius: 6px; padding: 14px 18px; margin-bottom: 12px; }}
.card .meta {{ color: {c['muted']}; font-size: .85rem; }}
.hero {{ border-bottom: 2px solid {c['accent']}; padding-bottom: 8px; margin-bottom: 18px; }}
.small-note {{ color: {c['muted']}; font-size: .85rem; }}
/* Responsive: tighter padding and stacked columns on small screens */
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
                      font=dict(family="Inter", color=c["text"]), margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def base_map(location, zoom, dark: bool) -> folium.Map:
    """OpenStreetMap base layer. Dark mode inverts the tiles with a CSS filter injected
    into the map itself (maps render inside an iframe, so page CSS cannot reach them)."""
    m = folium.Map(location=location, zoom_start=zoom, tiles="OpenStreetMap", control_scale=True)
    if dark:
        m.get_root().header.add_child(folium.Element(
            "<style>.leaflet-tile-pane{filter:invert(1) hue-rotate(180deg) brightness(.85) contrast(.9);}</style>"))
    return m
