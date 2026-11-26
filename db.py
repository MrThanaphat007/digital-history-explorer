"""SQLite layer + data validation.

Every CSV in data/ becomes a table named after the file (cities.csv -> cities).
To add a new dataset, drop a CSV into data/; the database rebuilds automatically.
A broken CSV is skipped (and reported by problems()) instead of crashing the whole app.
"""
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "history.db"

# Columns each known table must have (extra columns are allowed)
REQUIRED = {
    "events": ["id", "year", "title", "lat", "lon", "category", "description", "source"],
    "cities": ["name", "lat", "lon", "year_start", "region", "civilization", "note", "source"],
    "archive": ["id", "title", "date_text", "year", "region", "civilization", "type", "description", "source"],
    "population": ["metric", "entity", "year", "value", "unit", "source", "note"],
    "trade_routes": ["route", "seq", "node", "lat", "lon", "year_start", "note", "source"],
    "flows": ["metric", "flow", "start_year", "end_year", "value", "unit", "source", "note"],
    "impacts": ["id", "root_event_id", "parent_id", "label", "year", "detail", "certainty", "linked_event_id", "source"],
}


def _needs_rebuild() -> bool:
    """Rebuild when the DB is missing or any CSV is newer than it."""
    if not DB_PATH.exists():
        return True
    db_time = DB_PATH.stat().st_mtime
    return any(p.stat().st_mtime > db_time for p in DATA_DIR.glob("*.csv"))


@st.cache_resource(show_spinner=False)
def init_db() -> str:
    """Create/refresh the SQLite database from the CSV files (bad files are skipped)."""
    if _needs_rebuild():
        with sqlite3.connect(DB_PATH) as con:
            for csv in sorted(DATA_DIR.glob("*.csv")):
                try:
                    pd.read_csv(csv).to_sql(csv.stem, con, if_exists="replace", index=False)
                except Exception:
                    pass  # reported by problems()
    return str(DB_PATH)


@st.cache_data(show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a read-only SQL query and return a DataFrame."""
    with sqlite3.connect(init_db()) as con:
        return pd.read_sql_query(sql, con, params=params)


def tables() -> list[str]:
    return query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")["name"].tolist()


def _stamp() -> tuple:
    return tuple((p.name, p.stat().st_mtime) for p in sorted(DATA_DIR.glob("*.csv")))


@st.cache_data(show_spinner=False)
def _problems(stamp: tuple, data_dir: str) -> list[str]:
    out, frames = [], {}
    for csv in sorted(Path(data_dir).glob("*.csv")):
        try:
            frames[csv.stem] = pd.read_csv(csv)
        except Exception as e:
            out.append(f"{csv.name}: cannot be read ({str(e)[:90]}). Check for a missing quote or a wrong column count.")
    for name, cols in REQUIRED.items():
        df = frames.get(name)
        if df is None:
            if not any(name in p for p in out):
                out.append(f"{name}.csv: file is missing.")
            continue
        missing = [c for c in cols if c not in df.columns]
        if missing:
            out.append(f"{name}.csv: missing columns {', '.join(missing)}.")
            continue
        for c in ("lat", "lon", "year", "year_start", "value"):
            if name == "impacts" and c == "year":
                continue  # a branch may legitimately have no fixed year
            if c in df.columns and pd.to_numeric(df[c], errors="coerce").isna().any():
                out.append(f"{name}.csv: column '{c}' has a non-numeric or empty value.")
        if "lat" in df and not pd.to_numeric(df["lat"], errors="coerce").dropna().between(-90, 90).all():
            out.append(f"{name}.csv: a latitude is outside -90..90.")
        if "lon" in df and not pd.to_numeric(df["lon"], errors="coerce").dropna().between(-180, 180).all():
            out.append(f"{name}.csv: a longitude is outside -180..180.")
        if "id" in df and df["id"].duplicated().any():
            out.append(f"{name}.csv: duplicate ids: {', '.join(map(str, df['id'][df['id'].duplicated()].unique()[:5]))}.")
        if df["source"].isna().any():
            out.append(f"{name}.csv: {int(df['source'].isna().sum())} row(s) without a source.")
    imp, ev = frames.get("impacts"), frames.get("events")
    if imp is not None and ev is not None and all(c in imp for c in ("parent_id", "certainty")) and "id" in ev:
        bad = imp[imp["parent_id"].notna() & ~imp["parent_id"].isin(imp["id"])]
        if len(bad):
            out.append(f"impacts.csv: parent_id not found for: {', '.join(bad['id'].astype(str)[:5])}.")
        if (~imp["root_event_id"].isin(ev["id"])).any():
            out.append("impacts.csv: a root_event_id does not match any event id.")
        if (~imp["linked_event_id"].dropna().isin(ev["id"])).any():
            out.append("impacts.csv: a linked_event_id does not match any event id.")
        if (~imp["certainty"].isin(["established", "debated"])).any():
            out.append("impacts.csv: certainty must be 'established' or 'debated'.")
    return out


def problems() -> list[str]:
    """Human-readable list of data problems (empty list = all checks passed)."""
    return _problems(_stamp(), str(DATA_DIR))
