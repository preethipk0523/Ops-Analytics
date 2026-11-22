"""Generate a SIMULATED operations-ticket dataset with realistic data-quality problems.

Why simulate? So the project runs anywhere without downloads, and so we know exactly
which problems were injected and can check that the cleaning step fixes them.
The data is NOT real. Say so clearly if you show this project to anyone.

Run:  python -m src.generate_data
"""
import argparse

import numpy as np
import pandas as pd

from src.config import PRIORITIES, RAW_CSV, TEAMS


def generate(n_tickets: int = 20000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # 1) Creation timestamps: one year, busier on weekdays, slowly growing volume.
    start, end = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
    days = pd.date_range(start, end, freq="D")
    growth = np.linspace(0.8, 1.3, len(days))
    weekday_boost = np.where(days.dayofweek < 5, 1.0, 0.35)
    weights = growth * weekday_boost
    weights = weights / weights.sum()
    day_idx = rng.choice(len(days), size=n_tickets, p=weights)
    seconds = rng.integers(8 * 3600, 19 * 3600, size=n_tickets)  # 08:00-19:00
    created = days[day_idx] + pd.to_timedelta(seconds, unit="s")

    # 2) Attributes
    team = rng.choice(TEAMS, size=n_tickets, p=[0.30, 0.20, 0.18, 0.12, 0.20])
    priority = rng.choice(PRIORITIES, size=n_tickets, p=[0.05, 0.20, 0.50, 0.25])
    channel = rng.choice(["Email", "Phone", "Web form", "Chat"], size=n_tickets,
                         p=[0.40, 0.20, 0.25, 0.15])
    category = rng.choice(["Delay", "Access issue", "Data error", "Request", "Complaint"],
                          size=n_tickets, p=[0.25, 0.20, 0.15, 0.30, 0.10])
    assignee_id = rng.integers(1, 16, size=n_tickets)  # 15 agents

    # 3) Resolution time (hours): log-normal, faster for urgent work, slower for some teams.
    base = {"Critical": 3.0, "High": 7.0, "Medium": 20.0, "Low": 55.0}
    team_factor = {"Support": 1.0, "Billing": 1.1, "Logistics": 1.35,
                   "Onboarding": 0.9, "Technical": 1.25}
    mu = np.array([np.log(base[p] * team_factor[t]) for p, t in zip(priority, team)])
    res_hours = rng.lognormal(mean=mu, sigma=0.55)
    resolved = created + pd.to_timedelta(res_hours, unit="h")

    # 4) Tickets still open at the end of the year (more likely if created recently).
    cutoff = end + pd.Timedelta(days=1)
    still_open = (resolved > cutoff) | (rng.random(n_tickets) < 0.01)
    status = np.where(still_open, rng.choice(["Open", "In Progress"], size=n_tickets), "Resolved")
    resolved = pd.Series(resolved).where(~still_open, pd.NaT)

    df = pd.DataFrame({
        "ticket_id": [f"T{100000 + i}" for i in range(n_tickets)],
        "created_at": created,
        "resolved_at": resolved,
        "team": team,
        "category": category,
        "priority": priority,
        "channel": channel,
        "assignee_id": assignee_id,
        "status": status,
    })
    df = df.sort_values("created_at").reset_index(drop=True)
    return inject_quality_problems(df, rng)


def inject_quality_problems(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Make the data messy on purpose, like real exports from spreadsheets/internal tools."""
    df = df.copy()
    n = len(df)
    # Dates become text, as they would in a CSV export.
    df["created_at"] = df["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["resolved_at"] = df["resolved_at"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Inconsistent team names: lower case, UPPER case, extra spaces.
    idx = rng.choice(n, size=int(0.06 * n), replace=False)
    df.loc[idx, "team"] = [rng.choice([t.lower(), t.upper(), f" {t} "])
                           for t in df.loc[idx, "team"]]
    # Missing priority.
    df.loc[rng.choice(n, size=int(0.02 * n), replace=False), "priority"] = np.nan
    # Placeholder text instead of a real empty value.
    resolved_rows = df.index[df["resolved_at"].notna()]
    df.loc[rng.choice(resolved_rows, size=int(0.005 * n), replace=False), "resolved_at"] = "N/A"
    # Impossible times: resolved before created.
    bad = rng.choice(resolved_rows, size=int(0.008 * n), replace=False)
    for i in bad:
        ts = pd.to_datetime(df.loc[i, "created_at"], errors="coerce")
        if pd.notna(ts) and df.loc[i, "resolved_at"] != "N/A":
            df.loc[i, "resolved_at"] = (ts - pd.Timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    # Duplicate rows (the same ticket exported twice).
    dup = df.sample(int(0.01 * n), random_state=1)
    df = pd.concat([df, dup], ignore_index=True).sample(frac=1, random_state=2).reset_index(drop=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=20000, help="number of tickets")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    df = generate(args.n, args.seed)
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_CSV, index=False)
    print(f"Wrote {len(df):,} rows to {RAW_CSV}")


if __name__ == "__main__":
    main()
