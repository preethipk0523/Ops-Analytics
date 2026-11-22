# Build the dashboard in Power BI (optional second version)

Power BI Desktop runs on Windows. The project produces CSV files, so no database driver is needed.

## 1. Load the data
1. Run the pipeline so that `data/clean/tickets_clean.csv` and `outputs/kpis/*.csv` exist.
2. Power BI Desktop: **Get data > Text/CSV**, load `tickets_clean.csv`.
3. Open **Transform data** (Power Query) and check the types: `created_at` and `resolved_at`
   as Date/Time, `resolution_hours` and `sla_target_hours` as Decimal number,
   `sla_met` and `is_resolved` as True/False or Whole number.
4. Add a **Date table** (Modeling > New table) and relate it to `created_at`:
   ```DAX
   Calendar = CALENDAR(DATE(2025,1,1), DATE(2025,12,31))
   ```

## 2. Measures (Modeling > New measure)
```DAX
Total Tickets   = COUNTROWS(tickets_clean)
Open Tickets    = CALCULATE([Total Tickets], tickets_clean[is_resolved] = FALSE())
Avg Resolution Hours = AVERAGE(tickets_clean[resolution_hours])
SLA Adherence % = DIVIDE(
                    CALCULATE(COUNTROWS(tickets_clean), tickets_clean[sla_met] = TRUE()),
                    CALCULATE(COUNTROWS(tickets_clean), NOT ISBLANK(tickets_clean[sla_met])))
Tickets Last Month = CALCULATE([Total Tickets], DATEADD('Calendar'[Date], -1, MONTH))
```
(If `sla_met` was loaded as 0/1, replace `TRUE()` with `1`.)

## 3. Report page
- 4 **cards**: Total Tickets, Open Tickets, Avg Resolution Hours, SLA Adherence %.
- **Line and clustered column chart**: month on the axis, Total Tickets as columns, SLA Adherence % as line.
- **Bar chart**: SLA Adherence % by team.
- **Matrix**: priority by team with SLA Adherence %, conditional formatting (red below 50%).
- **Slicers**: team, priority, date.
- A text box with the **definition of each KPI** so a reader does not have to ask.

Compare the numbers with `outputs/kpis/overall_summary.csv`. They must match.
