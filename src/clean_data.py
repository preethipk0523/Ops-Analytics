"""Clean the raw ticket export and write a data-quality report.

Every cleaning rule is a small function so it can be unit-tested and explained.

Run:  python -m src.clean_data
"""
import pandas as pd

from src.config import CLEAN_CSV, PRIORITIES, QUALITY_REPORT, RAW_CSV, SLA_TARGET_HOURS, TEAMS

TEAM_LOOKUP = {t.lower(): t for t in TEAMS}
PRIORITY_LOOKUP = {p.lower(): p for p in PRIORITIES}


def standardise_text(df: pd.DataFrame) -> pd.DataFrame:
    """Trim spaces and map team / priority to their official spelling."""
    df = df.copy()
    df["team"] = df["team"].astype("string").str.strip().str.lower().map(TEAM_LOOKUP)
    df["priority"] = (df["priority"].astype("string").str.strip().str.lower()
                      .map(PRIORITY_LOOKUP).fillna("Unknown"))
    df["status"] = df["status"].astype("string").str.strip().str.title()
    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Turn text into real timestamps; unparseable values (e.g. 'N/A') become missing."""
    df = df.copy()
    for col in ("created_at", "resolved_at"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset="ticket_id", keep="first").reset_index(drop=True)


def flag_invalid_times(df: pd.DataFrame) -> pd.DataFrame:
    """Resolved before created is impossible: keep the row but blank the bad timestamp."""
    df = df.copy()
    invalid = df["resolved_at"].notna() & (df["resolved_at"] < df["created_at"])
    df["had_invalid_time"] = invalid
    df.loc[invalid, "resolved_at"] = pd.NaT
    return df


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add resolution time and SLA columns used by every KPI."""
    df = df.copy()
    df["resolution_hours"] = (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 3600
    df["sla_target_hours"] = df["priority"].map(SLA_TARGET_HOURS)  # NaN for 'Unknown'
    measurable = df["resolution_hours"].notna() & df["sla_target_hours"].notna()
    df["sla_met"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    df.loc[measurable, "sla_met"] = (df.loc[measurable, "resolution_hours"]
                                     <= df.loc[measurable, "sla_target_hours"])
    df["is_resolved"] = df["resolved_at"].notna()
    return df


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Run all steps in order and return the clean data plus counts for the report."""
    stats = {"rows_raw": len(raw)}
    df = drop_duplicates(raw)
    stats["duplicates_removed"] = stats["rows_raw"] - len(df)
    # Count problems BEFORE fixing them, so the report can say what was wrong.
    stats["team_spelling_fixed"] = int((~df["team"].isin(TEAMS)).sum())
    stats["priority_missing"] = int(df["priority"].isna().sum())
    stats["resolved_at_placeholders"] = int(
        (df["resolved_at"].astype("string").str.strip().str.upper() == "N/A").sum())
    df = standardise_text(df)
    df = parse_dates(df)
    df = flag_invalid_times(df)
    stats["invalid_time_rows"] = int(df["had_invalid_time"].sum())
    df = add_metrics(df)
    stats["rows_clean"] = len(df)
    stats["unmapped_team"] = int(df["team"].isna().sum())
    return df, stats


def write_report(stats: dict, df: pd.DataFrame) -> str:
    sla = df["sla_met"].dropna()
    lines = [
        "# Data quality report", "",
        "| Check | Result |", "|---|---|",
        f"| Rows in raw file | {stats['rows_raw']:,} |",
        f"| Duplicate tickets removed | {stats['duplicates_removed']:,} |",
        f"| Team names with wrong spelling/case/spaces (fixed) | {stats['team_spelling_fixed']:,} |",
        f"| Missing priority (set to 'Unknown') | {stats['priority_missing']:,} |",
        f"| `N/A` placeholders in resolved_at (now empty) | {stats['resolved_at_placeholders']:,} |",
        f"| Resolved-before-created rows (timestamp blanked) | {stats['invalid_time_rows']:,} |",
        f"| Team names that could not be mapped | {stats['unmapped_team']:,} |",
        f"| Rows in clean file | {stats['rows_clean']:,} |",
        f"| Tickets with a measurable SLA | {len(sla):,} |", "",
        "Rules: duplicates keep the first row; priority 'Unknown' is excluded from SLA "
        "calculations; open tickets have no resolution time.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False, na_values=[""])
    df, stats = clean(raw)
    CLEAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_CSV, index=False)
    QUALITY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT.write_text(write_report(stats, df), encoding="utf-8")
    print(f"Clean file: {CLEAN_CSV}  ({len(df):,} rows)")
    print(f"Report: {QUALITY_REPORT}")


if __name__ == "__main__":
    main()
