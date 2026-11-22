import sqlite3

import pandas as pd

from src.clean_data import clean
from src.load_db import load
from src.run_kpis import run_all, split_queries
from src.config import SQL_DIR
from tests.test_cleaning import make_raw


def build_db() -> sqlite3.Connection:
    df, _ = clean(make_raw())
    conn = sqlite3.connect(":memory:")
    load(df, conn)
    return conn


def test_all_queries_are_found():
    names = split_queries((SQL_DIR / "kpi_queries.sql").read_text(encoding="utf-8"))
    assert "overall_summary" in names and "weekly_backlog" in names and len(names) == 8


def test_overall_summary_matches_hand_calculation():
    results = run_all(build_db())
    s = results["overall_summary"].iloc[0]
    assert s["total_tickets"] == 4        # one duplicate removed
    assert s["resolved_tickets"] == 1     # only T1 has a valid resolved_at
    assert s["open_tickets"] == 3


def test_every_query_returns_a_dataframe():
    for name, df in run_all(build_db()).items():
        assert isinstance(df, pd.DataFrame), name
