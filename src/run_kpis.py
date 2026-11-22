"""Run every query in sql/kpi_queries.sql and save each result as a CSV.

These CSVs are what you connect Power BI / Excel to (see docs/powerbi_guide.md).

Run:  python -m src.run_kpis
"""
import re
import sqlite3

import pandas as pd

from src.config import DB_PATH, KPI_DIR, SQL_DIR


def split_queries(sql_text: str) -> dict[str, str]:
    """Split the SQL file into {name: query} using the '-- name: xxx' markers."""
    parts = re.split(r"^-- name:\s*(\w+)\s*$", sql_text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run_all(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    queries = split_queries((SQL_DIR / "kpi_queries.sql").read_text(encoding="utf-8"))
    return {name: pd.read_sql_query(sql, conn) for name, sql in queries.items()}


def main() -> None:
    KPI_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        results = run_all(conn)
    for name, df in results.items():
        df.to_csv(KPI_DIR / f"{name}.csv", index=False)
        print(f"{name:35s} {len(df):5d} rows")


if __name__ == "__main__":
    main()
