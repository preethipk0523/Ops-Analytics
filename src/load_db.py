"""Load the clean CSV into a SQLite database (a single file, no server needed).

Run:  python -m src.load_db
"""
import sqlite3

import pandas as pd

from src.config import CLEAN_CSV, DB_PATH, SQL_DIR

COLUMNS = ["ticket_id", "created_at", "resolved_at", "team", "category", "priority", "channel",
           "assignee_id", "status", "had_invalid_time", "resolution_hours", "sla_target_hours",
           "sla_met", "is_resolved"]


def load(df: pd.DataFrame, conn: sqlite3.Connection) -> int:
    conn.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    out = df[COLUMNS].copy()
    for col in ("created_at", "resolved_at"):
        out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
    for col in ("had_invalid_time", "is_resolved", "sla_met"):
        out[col] = out[col].map({True: 1, False: 0, "True": 1, "False": 0})
    out = out.astype(object).where(out.notna(), None)  # NaN/NaT -> NULL
    placeholders = ",".join("?" * len(COLUMNS))
    conn.executemany(f"INSERT INTO tickets ({','.join(COLUMNS)}) VALUES ({placeholders})",
                     out.itertuples(index=False, name=None))
    conn.commit()
    return len(out)


def main() -> None:
    df = pd.read_csv(CLEAN_CSV)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        n = load(df, conn)
    print(f"Loaded {n:,} rows into {DB_PATH}")


if __name__ == "__main__":
    main()
