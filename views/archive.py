"""Digital archive with search and filters."""
import folium
import streamlit as st
from streamlit_folium import st_folium
from db import query
from utils import base_map, fmt_year, era_of, ERAS, cert_badge, src_link


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>Digital Historical Archive</h1></div>", unsafe_allow_html=True)
    df = query("SELECT * FROM archive ORDER BY year")
    df["era"] = df["year"].map(era_of)

    q = st.text_input("Search title, description or source")
    c1, c2, c3, c4 = st.columns(4)
    era = c1.multiselect("Period", ERAS)
    reg = c2.multiselect("Region", sorted(df["region"].unique()))
    civ = c3.multiselect("Civilization", sorted(df["civilization"].unique()))
    typ = c4.multiselect("Type", sorted(df["type"].unique()))

    # Apply each filter only when something was chosen (Pandas boolean masks)
    if q:
        mask = df[["title", "description", "source"]].apply(lambda s: s.str.contains(q, case=False, na=False)).any(axis=1)
        df = df[mask]
    for col, sel in (("era", era), ("region", reg), ("civilization", civ), ("type", typ)):
        if sel:
            df = df[df[col].isin(sel)]

    st.write(f"**{len(df)}** entries")
    for r in df.itertuples():
        st.markdown(f"<div class='card'><h4 style='margin:0'>{r.title}</h4>"
                    f"<div class='meta'>{r.date_text}{cert_badge(getattr(r, 'date_certainty', None))} - {r.type} - {r.civilization} ({r.region})</div>"
                    f"<p>{r.description}</p><div class='meta'>Source: {src_link(r.source, getattr(r, 'url', None))}</div></div>", unsafe_allow_html=True)

    located = df.dropna(subset=["lat", "lon"])
    if not located.empty:
        st.subheader("Related locations")
        m = base_map((30, 20), 2, dark)
        for r in located.itertuples():
            folium.Marker((r.lat, r.lon), tooltip=f"{r.title} ({r.date_text})").add_to(m)
        st_folium(m, height=380, use_container_width=True, returned_objects=[], key=f"arch_{len(located)}_{q}")
