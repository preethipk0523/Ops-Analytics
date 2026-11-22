-- Table that holds the cleaned tickets (loaded by src/load_db.py).
DROP TABLE IF EXISTS tickets;
CREATE TABLE tickets (
    ticket_id        TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL,   -- 'YYYY-MM-DD HH:MM:SS'
    resolved_at      TEXT,            -- NULL while the ticket is open
    team             TEXT NOT NULL,
    category         TEXT,
    priority         TEXT NOT NULL,   -- Critical / High / Medium / Low / Unknown
    channel          TEXT,
    assignee_id      INTEGER,
    status           TEXT,
    had_invalid_time INTEGER,         -- 1 if resolved_at was before created_at in the raw data
    resolution_hours REAL,
    sla_target_hours REAL,
    sla_met          INTEGER,         -- 1 / 0, NULL when not measurable
    is_resolved      INTEGER
);
CREATE INDEX idx_tickets_created ON tickets (created_at);
CREATE INDEX idx_tickets_team ON tickets (team);
