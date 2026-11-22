"""Shared settings: paths and business rules used across the project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "raw" / "raw_tickets.csv"
CLEAN_CSV = ROOT / "data" / "clean" / "tickets_clean.csv"
QUALITY_REPORT = ROOT / "outputs" / "data_quality_report.md"
DB_PATH = ROOT / "data" / "ops.db"
KPI_DIR = ROOT / "outputs" / "kpis"
SQL_DIR = ROOT / "sql"

# Business rule: how many hours a ticket may take before the SLA is breached.
SLA_TARGET_HOURS = {"Critical": 4, "High": 8, "Medium": 24, "Low": 72}

TEAMS = ["Support", "Billing", "Logistics", "Onboarding", "Technical"]
PRIORITIES = list(SLA_TARGET_HOURS)
