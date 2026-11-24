"""SQLite layer.

Every CSV in data/ becomes a table named after the file (cities.csv -> cities).
To add a new dataset, drop a CSV into data/; the database rebuilds automatically.
"""
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "history.db"


def _needs_rebuild() -> bool:
    """Rebuild when the DB is missing or any CSV is newer than it."""
    if not DB_PATH.exists():
        return True
    db_time = DB_PATH.stat().st_mtime
    return any(p.stat().st_mtime > db_time for p in DATA_DIR.glob("*.csv"))


@st.cache_resource(show_spinner=False)
def init_db() -> str:
    """Create/refresh the SQLite database from the CSV files."""
    if _needs_rebuild():
        with sqlite3.connect(DB_PATH) as con:
            for csv in sorted(DATA_DIR.glob("*.csv")):
                pd.read_csv(csv).to_sql(csv.stem, con, if_exists="replace", index=False)
    return str(DB_PATH)


@st.cache_data(show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a read-only SQL query and return a DataFrame."""
    with sqlite3.connect(init_db()) as con:
        return pd.read_sql_query(sql, con, params=params)


def tables() -> list[str]:
    return query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")["name"].tolist()
