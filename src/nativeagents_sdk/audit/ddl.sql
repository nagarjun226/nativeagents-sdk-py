-- =====================================================================
-- Native Agents SDK — audit schema v1
-- =====================================================================
-- This schema is the contract between plugins, the SDK, and (eventually)
-- the Native Agents sidecar. Do NOT modify in place; use a migration.
-- =====================================================================

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Initial meta row: schema version.
-- Migrations update this value.
INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1');
INSERT OR IGNORE INTO meta (key, value) VALUES ('created_at', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));

-- ---------------------------------------------------------------------
-- events — the append-only audit log
-- ---------------------------------------------------------------------
-- Every observation any plugin records lands here.
-- Ordering within a session: strictly monotonic `sequence` starting at 1.
-- Ordering across sessions: by `timestamp` (observed) or `captured_at` (wall-clock at write).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    -- Row identity
    id               INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Event identity
    session_id       TEXT    NOT NULL,
    sequence         INTEGER NOT NULL,            -- per-session monotonic, starting at 1
    event_type       TEXT    NOT NULL,            -- e.g. "PreToolUse", or plugin-defined like "my-plugin.observation"
    plugin_name      TEXT    NOT NULL,            -- which plugin wrote this row

    -- Payload (opaque JSON, plugins own the shape for their own event_types)
    payload_json     TEXT    NOT NULL,            -- canonical JSON (UTF-8, sorted keys, no whitespace)
    payload_bytes    INTEGER NOT NULL,            -- len(payload_json) for quick stats

    -- Time
    timestamp        TEXT    NOT NULL,            -- ISO-8601 UTC — the EVENT's occurrence time
    captured_at      TEXT    NOT NULL,            -- ISO-8601 UTC — write time (may differ if spooled)

    -- Hash chain
    prev_hash        TEXT,                        -- SHA-256 hex of the previous row in this session's chain; NULL only for sequence=1
    row_hash         TEXT NOT NULL,               -- SHA-256 hex of (prev_hash || canonical_json(this_row_without_row_hash_field))

    -- Integrity constraints
    UNIQUE (session_id, sequence),
    CHECK (sequence >= 1),
    CHECK (length(row_hash) = 64),
    CHECK (prev_hash IS NULL OR length(prev_hash) = 64)
);

CREATE INDEX IF NOT EXISTS idx_events_session_seq ON events (session_id, sequence);
CREATE INDEX IF NOT EXISTS idx_events_event_type  ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_plugin      ON events (plugin_name);
CREATE INDEX IF NOT EXISTS idx_events_captured    ON events (captured_at);

-- ---------------------------------------------------------------------
-- sessions — lightweight session registry (optional denormalization)
-- ---------------------------------------------------------------------
-- Not part of the hash chain. Rebuilt from events on demand by plugins.
-- The SDK does NOT write here; agentaudit does via its projections layer.
-- The SDK creates the table for convenience but doesn't populate it.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    session_id       TEXT PRIMARY KEY,
    started_at       TEXT NOT NULL,
    ended_at         TEXT,
    agent_framework  TEXT NOT NULL DEFAULT 'claude-code',
    cwd              TEXT,
    extra_json       TEXT                          -- plugin-extensible metadata
);

-- ---------------------------------------------------------------------
-- sync_state — for the future sidecar's cursor (reserved, unused in OSS)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- End of schema v1.
