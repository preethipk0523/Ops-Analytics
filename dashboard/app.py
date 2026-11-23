"""Streamlit dashboard on top of the SQLite database.

Run:  streamlit run dashboard/app.py
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DB_PATH  # noqa: E402

st.set_page_config(page_title="Operations Performance", layout="wide")
st.title("Operations Performance Dashboard")
st.caption("Simulated ticket data. Filters on the left apply to every chart.")


@st.cache_data
def load_tickets() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM tickets", conn, parse_dates=["created_at", "resolved_at"])
    return df


df = load_tickets()

# ---- Sidebar filters --------------------------------------------------------------
teams = st.sidebar.multiselect("Team", sorted(df["team"].unique()), default=sorted(df["team"].unique()))
priorities = st.sidebar.multiselect("Priority", sorted(df["priority"].unique()),
                                    default=sorted(df["priority"].unique()))
min_d, max_d = df["created_at"].min().date(), df["created_at"].max().date()
date_range = st.sidebar.date_input("Created between", (min_d, max_d), min_value=min_d, max_value=max_d)
if len(date_range) != 2:
    st.stop()

mask = (df["team"].isin(teams) & df["priority"].isin(priorities)
        & (df["created_at"].dt.date >= date_range[0]) & (df["created_at"].dt.date <= date_range[1]))
f = df[mask]
if f.empty:
    st.warning("No tickets match the filters.")
    st.stop()

# ---- KPI cards --------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tickets", f"{len(f):,}")
c2.metric("Open tickets", f"{int((f['is_resolved'] == 0).sum()):,}")
c3.metric("Avg resolution (h)", f"{f['resolution_hours'].mean():.1f}")
c4.metric("SLA adherence", f"{100 * f['sla_met'].mean():.1f}%")

# ---- Charts -----------------------------------------------------------------------
left, right = st.columns(2)
monthly = f.groupby(f["created_at"].dt.to_period("M").astype(str)).agg(
    tickets=("ticket_id", "count"), sla=("sla_met", "mean"))
left.subheader("Tickets created per month")
left.bar_chart(monthly["tickets"])
right.subheader("SLA adherence per month (%)")
sla_month = (monthly["sla"] * 100).round(1).reset_index()
sla_month.columns = ["month", "sla"]
right.altair_chart(
    alt.Chart(sla_month).mark_line(point=True).encode(
        x=alt.X("month:N", title=None),
        y=alt.Y("sla:Q", title="SLA %", scale=alt.Scale(domain=[0, 100])),
    ),
    use_container_width=True,
)

by_team = f.groupby("team").agg(avg_hours=("resolution_hours", "mean"), sla=("sla_met", "mean"))
left.subheader("SLA adherence by team (%)")
left.bar_chart((by_team["sla"] * 100).round(1))
right.subheader("Average resolution time by team (hours)")
right.bar_chart(by_team["avg_hours"].round(1))

st.subheader("Slowest 10 resolved tickets")
st.dataframe(f.nlargest(10, "resolution_hours")[
    ["ticket_id", "team", "priority", "category", "created_at", "resolution_hours", "sla_target_hours"]],
    width="stretch")
