"""About & Methods: methodology, limitations, data downloads and automatic data checks."""
import streamlit as st
from db import query, tables, problems

REUSE_NOTE = ("Compiled for a college project. If you reuse the data, credit Digital History Explorer "
              "and the original source named in each row. Border polygons come from Historical Basemaps "
              "(A. Ourednik, github.com/aourednik/historical-basemaps); see that project for its licence.")


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>About &amp; Methods</h1><p class='small-note'>How the data was "
                "made, what it can and cannot show, and how to reuse it.</p></div>", unsafe_allow_html=True)
    st.subheader("Purpose")
    st.write("Digital History Explorer is a learning project on how maps, timelines, open data and "
             "archives can make historical research more accessible. It is a sample platform, not a finished "
             "scholarly atlas. The sample leans toward European history by design.")

    st.subheader("Methodology")
    st.markdown("""
- **Records.** Events, cities, archive items, population series and cause-and-effect links are stored as CSV files and loaded into SQLite. Each row names a source; where a verified web page was found, its link is stored too.
- **Borders.** Eleven snapshots (1000 BCE to 1945 CE) from the Historical Basemaps project, simplified for display. The map uses the snapshot nearest the selected year, which may be centuries away.
- **Spatial lookup.** The "which polity contained this place" result is a point-in-polygon test on those approximate polygons.
- **Date certainty.** *secure* = date well established; *approximate* = a "c." date, or a place or period that cannot be fixed exactly; *traditional* = a date handed down by tradition.
- **Cause and effect.** Links are interpretations. *Established* means the link is widely accepted; *debated* means historians disagree or the connection is indirect.
- **Trade routes** are schematic chains of major nodes, not exact paths.
""")

    st.subheader("Limitations")
    st.markdown("""
- A small sample: a few dozen events, mostly European and Mediterranean.
- Early borders were rarely fixed lines; polygons suggest more precision than the sources support.
- Population figures are modelled estimates. Census counts follow different definitions and cannot be compared directly.
- Many links point to general reference works. Check each against its source before citing it.
""")

    st.subheader("Data downloads")
    st.caption(REUSE_NOTE)
    cols = st.columns(3)
    for i, t in enumerate(tables()):
        df = query(f"SELECT * FROM {t}")
        cols[i % 3].download_button(f"{t}.csv ({len(df)} rows)", df.to_csv(index=False).encode("utf-8"),
                                    file_name=f"{t}.csv", mime="text/csv", key=f"dl_{t}")

    st.subheader("Data checks")
    issues = problems()
    if issues:
        st.warning("Some data problems were found:")
        for p in issues:
            st.write("- " + p)
    else:
        st.success("All automatic checks passed: columns present, numbers valid, ids unique, links consistent.")
    st.subheader("How to cite")
    st.code("Digital History Explorer (2026). Sample historical dataset and viewer. Accessed [date].", language=None)
