"""Interactive timeline linked to the map and to GIS (polity lookup)."""
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium
import folium
from db import query
from geo import polity_at
from utils import base_map, fmt_year, year_ticks, style_fig, ERA_RANGES, YEAR_MIN, YEAR_MAX


def _show_on_map(row):
    """Callback: store the event, move the global year, and jump to the map page."""
    st.session_state["focus_event"] = {"lat": row["lat"], "lon": row["lon"], "title": row["title"]}
    st.session_state["year"] = int(row["year"])
    st.session_state["nav"] = "Interactive Map"


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>Historical Timeline</h1></div>", unsafe_allow_html=True)
    preset = st.radio("Era", list(ERA_RANGES), horizontal=True)
    lo, hi = ERA_RANGES[preset] or st.slider("Year range", YEAR_MIN, YEAR_MAX, (-500, 1500), 10,
                                              help="Negative values are BCE")
    cats = query("SELECT DISTINCT category FROM events ORDER BY category")["category"].tolist()
    chosen = st.multiselect("Categories", cats, default=cats)

    df = query("SELECT * FROM events WHERE year BETWEEN ? AND ? ORDER BY year", (lo, hi))
    df = df[df["category"].isin(chosen)]
    if df.empty:
        st.info("No events in this range. Add rows to data/events.csv to extend the timeline.")
        return

    df = df.assign(label=df["year"].map(fmt_year))
    fig = px.scatter(df, x="year", y="category", color="category", hover_name="title",
                     hover_data={"label": True, "year": False, "category": False}, size_max=14)
    fig.update_traces(marker=dict(size=14, line=dict(width=1, color="#444")))
    tv, tt = year_ticks(df["year"])
    fig.update_xaxes(tickvals=tv, ticktext=tt, title="")
    fig.update_yaxes(title="")
    fig.add_vline(x=year, line_dash="dot", line_color="#b08d57", annotation_text="selected year")
    st.plotly_chart(style_fig(fig, dark, 360), width="stretch")

    title = st.selectbox("Explore an event", df["title"], format_func=lambda t: f"{fmt_year(df[df.title == t].year.iloc[0])} - {t}")
    ev = df[df.title == title].iloc[0]
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"<div class='card'><h3>{ev.title}</h3><div class='meta'>{fmt_year(ev.year)} - {ev.category}</div>"
                    f"<p>{ev.description}</p><div class='meta'>Source: {ev.source}</div></div>", unsafe_allow_html=True)
        snap, polities = polity_at(ev.lat, ev.lon, int(ev.year))
        st.markdown(f"**GIS lookup:** in the {fmt_year(snap)} border snapshot (nearest to this event) the location "
                    f"falls within: **{', '.join(polities) if polities else 'no mapped polity'}**.")
        st.caption("Snapshots can be centuries away from the event, so treat this as context, not proof.")
        st.button("Show on map", on_click=_show_on_map, args=(ev.to_dict(),))
    with right:
        m = base_map((ev.lat, ev.lon), 5, dark)
        folium.Marker((ev.lat, ev.lon), tooltip=ev.title).add_to(m)
        st_folium(m, height=300, use_container_width=True, returned_objects=[], key=f"mini_{ev.id}")
