# Learning guide: how the project works

Read in this order. Run each step and open the output file before moving on.

## 1. The data (`src/generate_data.py`)
Creates 20,000 tickets for 2025 with random but realistic patterns: more tickets on weekdays,
volume growing over the year, urgent tickets resolved faster, some teams slower. Then
`inject_quality_problems` makes it messy on purpose.
**Look at:** `data/raw/raw_tickets.csv` (open it in Excel and find the bad rows yourself first).

Key idea: real data is never clean. A data analyst spends much of the time checking quality.

## 2. Cleaning (`src/clean_data.py`)
One small function per rule, so each can be tested:

| Function | Problem solved | Decision you could be asked to defend |
|---|---|---|
| `drop_duplicates` | same ticket exported twice | keep the first row |
| `standardise_text` | `support` / `SUPPORT` / ` Support ` | map to an official list; missing priority becomes `Unknown` |
| `parse_dates` | dates stored as text, `N/A` placeholders | unparseable becomes empty, not an error |
| `flag_invalid_times` | resolved before created | keep the ticket, blank the bad timestamp, flag it |
| `add_metrics` | need KPIs | compute hours, SLA target, SLA met; `Unknown` priority is excluded from SLA |

**Look at:** `outputs/data_quality_report.md`. It counts what was wrong *before* fixing it.

## 3. Database (`sql/schema.sql`, `src/load_db.py`)
SQLite is a database in a single file, so there is nothing to install. The schema defines
types and indexes. `load_db.py` converts pandas values to SQL values (True/False to 1/0,
NaN to NULL).
**Try:** open `data/ops.db` with *DB Browser for SQLite* and run `SELECT * FROM tickets LIMIT 10;`.

## 4. KPI queries (`sql/kpi_queries.sql`), the core of the project
| Query | SQL concept |
|---|---|
| `overall_summary` | aggregates, `AVG` of a 0/1 column gives a percentage |
| `monthly_volume_and_sla` | `GROUP BY` with `strftime` |
| `team_performance` | `RANK() OVER (...)` |
| `sla_by_priority` | filtering and ordering |
| `weekly_backlog` | two CTEs, `LEFT JOIN`, running `SUM() OVER (ORDER BY ...)` |
| `daily_volume_rolling_7d` | moving average with `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` |
| `agent_workload` | `AVG() OVER ()` and `NTILE(4)` |
| `breaches_by_category_and_channel` | multi-column `GROUP BY` |

`src/run_kpis.py` finds each query by its `-- name:` comment, runs it, and saves a CSV.
**Look at:** `outputs/kpis/`. Check one number by hand (for example the open ticket count).

## 5. Dashboard (`dashboard/app.py`)
Reads the `tickets` table, applies the sidebar filters, shows KPI cards and charts.
Streamlit reruns the script top to bottom every time a filter changes, and
`@st.cache_data` stops it reloading the data each time.

## 6. Tests and CI
`tests/test_cleaning.py` checks each rule on a 5-row example whose answers you can verify by
hand. `tests/test_sql.py` checks the SQL on a tiny in-memory database. The GitHub Actions
workflow runs both on every push, so a green tick shows the project works from a clean machine.

## Exercises (do at least three, then write them in the README)
1. Add a **first-response time** column to the generator, clean it, and add a KPI.
2. Add a rule that flags **weekend tickets** and compare their SLA with weekday tickets.
3. Write a query for the **top 3 categories per team** using `ROW_NUMBER() OVER (PARTITION BY ...)`.
4. Replace the simulated data with a **real public dataset** (for example open data from
   data.gouv.fr) and adapt the cleaning rules.
5. Add a **forecast** of next month's ticket volume (moving average first, then a simple model)
   and compare it with the actual figures.
6. Rebuild the dashboard in Power BI (`docs/powerbi_guide.md`) and compare both.

## Questions you should be able to answer
- Why simulate the data, and what are the limits of that?
- Why is `Unknown` priority excluded from SLA adherence rather than counted as breached?
- Why keep a ticket whose resolved date is before its created date instead of deleting it?
- How does `AVG(sla_met)` give a percentage, and what happens to NULL rows?
- How is the backlog computed, and why does it end at the number of open tickets?
- What would change if this ran every day on a real database?
