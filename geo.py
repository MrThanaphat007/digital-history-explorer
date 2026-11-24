"""Historical GIS helpers built on GeoPandas.

Border snapshots come from data/borders/world_<year>.geojson ("bc500" = 500 BCE).
Source: Historical Basemaps by A. Ourednik (github.com/aourednik/historical-basemaps).
Add a new period by copying another snapshot file into data/borders/.
"""
import re
import zlib
import geopandas as gpd
import streamlit as st
from shapely.geometry import Point
from db import DATA_DIR

BORDER_DIR = DATA_DIR / "borders"


@st.cache_data(show_spinner=False)
def snapshots() -> dict[int, str]:
    """Map snapshot year (negative = BCE) -> file path."""
    out = {}
    for p in BORDER_DIR.glob("world_*.geojson"):
        m = re.match(r"world_(bc)?(\d+)", p.stem)
        if m:
            out[-int(m.group(2)) if m.group(1) else int(m.group(2))] = str(p)
    return dict(sorted(out.items()))


def nearest_snapshot(year: int) -> int:
    return min(snapshots(), key=lambda y: abs(y - year))


@st.cache_data(show_spinner="Loading borders...")
def load_borders(year: int) -> gpd.GeoDataFrame:
    """Load a snapshot, drop unnamed areas and simplify geometry for fast rendering."""
    g = gpd.read_file(snapshots()[year])
    g = g[g["NAME"].notna()].copy()
    g["geometry"] = g.geometry.simplify(0.05, preserve_topology=True)
    g = g.set_crs(4326, allow_override=True)
    return g[["NAME", "geometry"]]


def colour_for(name: str) -> str:
    """Stable colour per polity name (crc32 is stable between runs, unlike hash())."""
    palette = ["#7a1f2b", "#b08d57", "#3f6b5c", "#4a5d8a", "#8a5a83", "#a8602f",
               "#5b7f95", "#6b6b3a", "#9c4a4a", "#487a7a", "#7d6a4f", "#5c4b8a"]
    return palette[zlib.crc32(name.encode()) % len(palette)]


def polity_at(lat: float, lon: float, year: int):
    """Spatial lookup: which mapped polity contains this point in the nearest snapshot?"""
    snap = nearest_snapshot(year)
    g = load_borders(snap)
    hits = g[g.contains(Point(lon, lat))]
    return snap, sorted(set(hits["NAME"]))


@st.cache_data(show_spinner=False)
def polity_summary(year: int):
    """Number of mapped polities and the largest by area (equal-area projection, approximate)."""
    g = load_borders(year).copy()
    g["area_km2"] = g.to_crs("EPSG:6933").area / 1e6
    top = (g.groupby("NAME", as_index=False)["area_km2"].sum()
             .sort_values("area_km2", ascending=False).head(8))
    top["area_km2"] = top["area_km2"].round(-3).astype(int)
    return g["NAME"].nunique(), top
