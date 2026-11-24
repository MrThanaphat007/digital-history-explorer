# Digital History Explorer

Interactive Digital Humanities platform: historical map (Folium + GeoPandas), linked timeline,
data analysis (Pandas + Plotly), digital archive and research dashboard. Data lives in SQLite.

## Run locally
    pip install -r requirements.txt
    streamlit run app.py

## Deploy (public URL, free)
1. Push this folder to a GitHub repository.
2. Go to share.streamlit.io, choose the repo, set the main file to `app.py`, deploy.

## Project structure
    app.py            navigation, global year slider, dark mode
    db.py             CSV -> SQLite loader and query helper
    geo.py            GeoPandas: border snapshots, polity lookup, area summary
    utils.py          year formatting, eras, theme, Plotly style, base map
    views/            one module per page (render(year, dark))
    data/*.csv        datasets (each row has a source)
    data/borders/     world_<year>.geojson border snapshots

## Adding data
- New events / cities / archive items: append rows to the matching CSV in `data/` (keep the `source` column).
- New dataset: drop a new CSV in `data/`; it becomes a SQLite table automatically.
- New period: copy another snapshot into `data/borders/` named `world_<year>.geojson` (`world_bc500.geojson` for BCE).
  More snapshots: github.com/aourednik/historical-basemaps
- New page: create `views/<name>.py` with `render(year, dark)` and register it in `PAGES` in `app.py`.

## Data integrity notes
- Population figures are rounded scholarly estimates (McEvedy & Jones 1978); other reconstructions differ.
- Han China and Roman figures are census *registrations*, with different definitions; do not compare them as total population.
- Trade routes are schematic chains of major nodes, not exact paths.
- Border polygons come from Historical Basemaps (approximate; see its documentation).
- Dates marked "c." or "traditional" are approximate. Verify against the cited source before academic citation.
