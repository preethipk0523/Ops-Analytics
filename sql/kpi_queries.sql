-- Each query starts with "-- name: <name>". src/run_kpis.py runs them all and
-- saves one CSV per query in outputs/kpis/.  Dialect: SQLite (3.25+ for window functions).

-- name: overall_summary
-- One row with the headline numbers of the whole year.
SELECT
    COUNT(*)                                                    AS total_tickets,
    SUM(is_resolved)                                            AS resolved_tickets,
    COUNT(*) - SUM(is_resolved)                                 AS open_tickets,
    ROUND(AVG(resolution_hours), 1)                             AS avg_resolution_hours,
    ROUND(100.0 * AVG(sla_met), 1)                              AS sla_adherence_pct
FROM tickets;

-- name: monthly_volume_and_sla
-- Tickets created per month, with average resolution time and SLA adherence.
SELECT
    strftime('%Y-%m', created_at)             AS month,
    COUNT(*)                                  AS tickets_created,
    ROUND(AVG(resolution_hours), 1)           AS avg_resolution_hours,
    ROUND(100.0 * AVG(sla_met), 1)            AS sla_adherence_pct
FROM tickets
GROUP BY month
ORDER BY month;

-- name: team_performance
-- Teams ranked by SLA adherence (window function RANK).
SELECT
    team,
    COUNT(*)                                          AS tickets,
    ROUND(AVG(resolution_hours), 1)                   AS avg_resolution_hours,
    ROUND(100.0 * AVG(sla_met), 1)                    AS sla_adherence_pct,
    RANK() OVER (ORDER BY AVG(sla_met) DESC)          AS sla_rank
FROM tickets
GROUP BY team
ORDER BY sla_rank;

-- name: sla_by_priority
-- Which priority levels miss their target most often.
SELECT
    priority,
    MAX(sla_target_hours)                     AS sla_target_hours,
    COUNT(sla_met)                            AS measurable_tickets,
    ROUND(AVG(resolution_hours), 1)           AS avg_resolution_hours,
    ROUND(100.0 * AVG(sla_met), 1)            AS sla_adherence_pct
FROM tickets
WHERE priority <> 'Unknown'
GROUP BY priority
ORDER BY sla_target_hours;

-- name: weekly_backlog
-- Backlog = tickets created so far minus tickets resolved so far.
-- Two CTEs count created and resolved tickets per week; a running SUM turns them into a backlog.
WITH created AS (
    SELECT strftime('%Y-W%W', created_at) AS week, COUNT(*) AS created_cnt
    FROM tickets GROUP BY week
),
resolved AS (
    SELECT strftime('%Y-W%W', resolved_at) AS week, COUNT(*) AS resolved_cnt
    FROM tickets WHERE resolved_at IS NOT NULL GROUP BY week
)
SELECT
    c.week,
    c.created_cnt,
    COALESCE(r.resolved_cnt, 0)                                        AS resolved_cnt,
    SUM(c.created_cnt - COALESCE(r.resolved_cnt, 0))
        OVER (ORDER BY c.week)                                         AS backlog
FROM created c
LEFT JOIN resolved r ON r.week = c.week
ORDER BY c.week;

-- name: daily_volume_rolling_7d
-- Daily ticket volume and its 7-day moving average (smooths weekday/weekend swings).
WITH daily AS (
    SELECT date(created_at) AS day, COUNT(*) AS tickets
    FROM tickets GROUP BY day
)
SELECT
    day,
    tickets,
    ROUND(AVG(tickets) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1)
        AS tickets_7d_avg
FROM daily
ORDER BY day;

-- name: agent_workload
-- Workload and speed per agent, compared with the team-wide average resolution time.
WITH per_agent AS (
    SELECT assignee_id,
           COUNT(*)                         AS tickets,
           AVG(resolution_hours)            AS avg_hours
    FROM tickets
    GROUP BY assignee_id
)
SELECT
    assignee_id,
    tickets,
    ROUND(avg_hours, 1)                                              AS avg_resolution_hours,
    ROUND(avg_hours - AVG(avg_hours) OVER (), 1)                     AS diff_vs_average_hours,
    NTILE(4) OVER (ORDER BY tickets DESC)                            AS workload_quartile
FROM per_agent
ORDER BY tickets DESC;

-- name: breaches_by_category_and_channel
-- Where do SLA breaches come from?  (sla_met = 0 means breached)
SELECT
    category,
    channel,
    COUNT(*)                                 AS breached_tickets
FROM tickets
WHERE sla_met = 0
GROUP BY category, channel
ORDER BY breached_tickets DESC
LIMIT 15;
