import pandas as pd

from src.clean_data import (add_metrics, clean, drop_duplicates, flag_invalid_times,
                            parse_dates, standardise_text)


def make_raw() -> pd.DataFrame:
    return pd.DataFrame({
        "ticket_id": ["T1", "T1", "T2", "T3", "T4"],
        "created_at": ["2025-01-01 09:00:00"] * 5,
        "resolved_at": ["2025-01-01 11:00:00", "2025-01-01 11:00:00", "N/A",
                        "2025-01-01 06:00:00", None],
        "team": ["support", "support", " BILLING ", "Logistics", "Technical"],
        "category": ["Delay"] * 5,
        "priority": ["High", "High", None, "Critical", "Low"],
        "channel": ["Email"] * 5,
        "assignee_id": ["1"] * 5,
        "status": ["Resolved", "Resolved", "Resolved", "Resolved", "Open"],
    })


def test_duplicates_removed():
    assert len(drop_duplicates(make_raw())) == 4


def test_team_and_priority_standardised():
    df = standardise_text(drop_duplicates(make_raw()))
    assert set(df["team"]) == {"Support", "Billing", "Logistics", "Technical"}
    assert df.loc[df["ticket_id"] == "T2", "priority"].iloc[0] == "Unknown"


def test_unparseable_date_becomes_missing():
    df = parse_dates(drop_duplicates(make_raw()))
    assert df.loc[df["ticket_id"] == "T2", "resolved_at"].isna().all()


def test_resolved_before_created_is_flagged_and_blanked():
    df = flag_invalid_times(parse_dates(drop_duplicates(make_raw())))
    row = df[df["ticket_id"] == "T3"].iloc[0]
    assert row["had_invalid_time"] and pd.isna(row["resolved_at"])


def test_sla_calculation():
    df, stats = clean(make_raw())
    t1 = df[df["ticket_id"] == "T1"].iloc[0]
    assert t1["resolution_hours"] == 2.0          # 09:00 -> 11:00
    assert t1["sla_target_hours"] == 8            # High priority
    assert bool(t1["sla_met"]) is True
    assert pd.isna(df.loc[df["ticket_id"] == "T2", "sla_met"].iloc[0])  # unknown priority
    assert stats["duplicates_removed"] == 1
    assert stats["rows_clean"] == 4


def test_add_metrics_open_ticket_has_no_resolution_time():
    df = add_metrics(parse_dates(standardise_text(make_raw().iloc[[4]])))
    assert pd.isna(df["resolution_hours"].iloc[0]) and not df["is_resolved"].iloc[0]
