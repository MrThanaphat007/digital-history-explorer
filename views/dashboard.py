"""Research dashboard: dataset overview, statistics, source transparency."""
import pandas as pd
import plotly.express as px
import streamlit as st
from db import query, tables
from geo import snapshots
from utils import fmt_year, style_fig


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>Digital History Explorer</h1>"
                "<p class='small-note'>An interactive research platform combining history, historical GIS, "
                "data analysis and information technology.</p></div>", unsafe_allow_html=True)
    ev, ci, ar = query("SELECT * FROM events"), query("SELECT * FROM cities"), query("SELECT * FROM archive")
    c = st.columns(5)
    c[0].metric("Events", len(ev))
    c[1].metric("Cities", len(ci))
    c[2].metric("Archive items", len(ar))
    c[3].metric("Border snapshots", len(snapshots()))
    c[4].metric("Time span", f"{fmt_year(ev.year.min())} – {fmt_year(ev.year.max())}")

    left, right = st.columns(2)
    with left:
        st.subheader("Events by category")
        cnt = ev["category"].value_counts().reset_index()
        cnt.columns = ["category", "events"]
        st.plotly_chart(style_fig(px.bar(cnt, x="category", y="events", color="category"), dark, 340),
                        width="stretch")
    with right:
        st.subheader("Where events happened")
        fig = px.scatter_geo(ev, lat="lat", lon="lon", color="category", hover_name="title",
                             hover_data={"year": True, "lat": False, "lon": False}, projection="natural earth")
        st.plotly_chart(style_fig(fig, dark, 340), width="stretch")

    st.subheader("Selected year at a glance")
    st.write(f"**{fmt_year(year)}** - adjust the year in the sidebar. Events within ±50 years:")
    near = ev[(ev.year >= year - 50) & (ev.year <= year + 50)][["year", "title", "category", "source"]]
    st.dataframe(near, hide_index=True, width="stretch") if len(near) else st.caption("None in the sample data.")

    st.subheader("Data sources")
    st.caption("Every dataset is a CSV in data/ with a source column. Rows are approximate or traditional where noted.")
    rows = []
    for t in tables():
        df = query(f"SELECT * FROM {t}")
        if "source" in df:
            for s in df["source"].dropna().unique():
                rows.append({"dataset": t, "source": s, "rows": int((df["source"] == s).sum())})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.markdown("Border polygons: *Historical Basemaps* by Andrei Ourednik (GitHub: aourednik/historical-basemaps), "
                "which documents its own limits in accuracy.")
