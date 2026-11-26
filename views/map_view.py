"""Interactive historical map (Folium) driven by the global year slider."""
import html
import folium
import streamlit as st
from streamlit_folium import st_folium
from db import query
from geo import snapshots, nearest_snapshot, load_borders, colour_for, polity_summary
from utils import fmt_year, base_map, cert_badge, src_link

CAT_COLOURS = {"War": "red", "Politics": "blue", "Law": "green", "Religion": "purple",
               "Exploration": "orange", "Disease": "black", "Trade": "darkgreen"}


def build_map(snap, year, dark, show_borders, show_cities, show_events, show_routes,
              window, focus=None, modern=False):
    """Build one Folium map. `snap` = border snapshot year, `year` = selected year."""
    centre, zoom = ((focus["lat"], focus["lon"]), 5) if focus else ((30, 20), 2)
    m = base_map(centre, zoom, dark, modern)

    if show_borders:
        g = load_borders(snap)
        folium.GeoJson(
            g, name=f"Borders ({fmt_year(snap)})",
            style_function=lambda f: {"fillColor": colour_for(f["properties"]["NAME"]),
                                      "color": "#444", "weight": 0.6, "fillOpacity": 0.45},
            tooltip=folium.GeoJsonTooltip(fields=["NAME"], aliases=["Polity:"]),
        ).add_to(m)

    if show_cities:
        grp = folium.FeatureGroup(name="Cities")
        for r in query("SELECT * FROM cities WHERE year_start <= ?", (year,)).itertuples():
            popup = (f"<b>{html.escape(r.name)}</b><br>{html.escape(r.civilization)} - "
                     f"{html.escape(r.region)}<br>From {fmt_year(r.year_start)}<br>"
                     f"{html.escape(r.note)}<br>{cert_badge(getattr(r, 'date_certainty', None))}<br>"
                     f"<i>Source: {src_link(r.source, getattr(r, 'url', None))}</i>")
            folium.CircleMarker((r.lat, r.lon), radius=6, color="#7a1f2b", fill=True,
                                fill_color="#d4b06a", fill_opacity=0.9,
                                tooltip=r.name, popup=folium.Popup(popup, max_width=300)).add_to(grp)
        grp.add_to(m)

    if show_routes:
        grp = folium.FeatureGroup(name="Trade routes")
        df = query("SELECT * FROM trade_routes WHERE year_start <= ? ORDER BY route, seq", (year,))
        for route, part in df.groupby("route"):
            folium.PolyLine(part[["lat", "lon"]].values.tolist(), color="#b08d57", weight=3,
                            dash_array="8 6", tooltip=route,
                            popup=f"{route}<br>{part.iloc[0]['note']}").add_to(grp)
        grp.add_to(m)

    if show_events:
        grp = folium.FeatureGroup(name="Events")
        df = query("SELECT * FROM events WHERE year BETWEEN ? AND ?", (year - window, year + window))
        for r in df.itertuples():
            popup = (f"<b>{html.escape(r.title)}</b><br>{fmt_year(r.year)} - {r.category}<br>"
                     f"{html.escape(r.description)}<br>{cert_badge(getattr(r, 'date_certainty', None))}<br>"
                     f"<i>Source: {src_link(r.source, getattr(r, 'url', None))}</i>")
            folium.Marker((r.lat, r.lon), tooltip=f"{r.title} ({fmt_year(r.year)})",
                          popup=folium.Popup(popup, max_width=300),
                          icon=folium.Icon(color=CAT_COLOURS.get(r.category, "gray"),
                                           icon="info-sign")).add_to(grp)
        grp.add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    return m


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>Interactive Historical Map</h1></div>", unsafe_allow_html=True)
    snaps = list(snapshots())
    snap = nearest_snapshot(year)
    st.caption(f"Selected year: **{fmt_year(year)}** - nearest border snapshot: **{fmt_year(snap)}**. "
               "Borders are approximate reconstructions (see Sources on the Dashboard).")

    c1, c2, c3, c4, c5 = st.columns(5)
    modern = st.checkbox("Add modern basemap (OpenStreetMap)", False)
    sb = c1.checkbox("Borders", True)
    sc = c2.checkbox("Cities", True)
    sr = c3.checkbox("Trade routes", True)
    se = c4.checkbox("Events", True)
    window = c5.slider("Event window (±yrs)", 10, 500, 100, 10)

    focus = st.session_state.get("focus_event")
    mode = st.radio("View", ["Single period", "Compare two periods"], horizontal=True)

    if mode == "Single period":
        m = build_map(snap, year, dark, sb, sc, se, sr, window, focus, modern)
        st_folium(m, height=560, use_container_width=True, returned_objects=[], key=f"map_{year}_{snap}_{modern}")
        n, top = polity_summary(snap)
        st.markdown(f"**{n} polities** are mapped in the {fmt_year(snap)} snapshot. Largest by area (approximate):")
        st.dataframe(top.rename(columns={"NAME": "Polity", "area_km2": "Area (km²)"}),
                     hide_index=True, width="stretch")
    else:
        a, b = st.columns(2)
        ya = a.selectbox("Period A", snaps, index=snaps.index(snap), format_func=fmt_year)
        yb = b.selectbox("Period B", snaps, index=min(len(snaps) - 1, snaps.index(snap) + 3),
                         format_func=fmt_year)
        for col, y, k in ((a, ya, "a"), (b, yb, "b")):
            with col:
                m = build_map(y, y, dark, sb, sc, False, sr, window, None, modern)
                st_folium(m, height=440, use_container_width=True, returned_objects=[], key=f"cmp_{k}_{y}_{modern}")
        na, ta = polity_summary(ya)
        nb, tb = polity_summary(yb)
        st.metric("Change in number of mapped polities", f"{nb - na:+d}", f"{na} → {nb}")
