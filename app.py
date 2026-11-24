"""Digital History Explorer - entry point.

Run with:  streamlit run app.py
Sidebar state shared by all pages: dark mode, selected year, navigation.
"""
import streamlit as st
from db import init_db
from utils import apply_theme, fmt_year, YEAR_MIN, YEAR_MAX
from views import dashboard, map_view, timeline, analysis, archive

st.set_page_config(page_title="Digital History Explorer", page_icon="🏛️", layout="wide")
init_db()  # build SQLite from CSVs on first run

PAGES = {  # to add a page: create views/<name>.py with render(year, dark) and register it here
    "Dashboard": dashboard,
    "Interactive Map": map_view,
    "Timeline": timeline,
    "Data Analysis": analysis,
    "Archive": archive,
}

st.session_state.setdefault("year", 100)
st.session_state.setdefault("nav", "Dashboard")

with st.sidebar:
    st.title("🏛️ Digital History Explorer")
    page = st.radio("Navigate", list(PAGES), key="nav")
    st.slider("Selected year (negative = BCE)", YEAR_MIN, YEAR_MAX, key="year", step=10)
    st.caption(f"Current: **{fmt_year(st.session_state['year'])}**")
    dark = st.toggle("Dark mode", value=False)
    st.markdown("<span class='small-note'>Sample datasets with listed sources. Approximate or traditional "
                "values are labelled; verify before academic citation.</span>", unsafe_allow_html=True)

apply_theme(dark)
PAGES[page].render(st.session_state["year"], dark)
