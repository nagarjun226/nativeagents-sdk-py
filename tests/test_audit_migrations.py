"""Tests for audit schema migrations."""

from __future__ import annotations

import sqlite3

from nativeagents_sdk.audit.migrations import (
    CURRENT_SCHEMA_VERSION,
    ensure_schema,
    migrate,
)
from nativeagents_sdk.audit.store import open_store


def test_current_schema_version_is_1():
    assert CURRENT_SCHEMA_VERSION == 1


def test_fresh_db_has_correct_schema(isolated_home):
    """Opening a new database creates schema with correct version."""
    conn = open_store()
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert row is not None
    assert int(row[0]) == 1
    conn.close()


def test_events_table_exists(isolated_home):
    """events table is created by the schema."""
    conn = open_store()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
    ).fetchone()
    assert row is not None
    conn.close()


def test_sessions_table_exists(isolated_home):
    """sessions table is created by the schema."""
    conn = open_store()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
    ).fetchone()
    assert row is not None
    conn.close()


def test_sync_state_table_exists(isolated_home):
    """sync_state table is created by the schema."""
    conn = open_store()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_state'"
    ).fetchone()
    assert row is not None
    conn.close()


def test_ensure_schema_idempotent(isolated_home):
    """ensure_schema() on an already-initialized DB is safe."""
    conn = open_store()
    ensure_schema(conn)  # Second call should not raise
    ensure_schema(conn)  # Third call too
    conn.close()


def test_migrate_already_current(isolated_home):
    """Migrating a DB already at CURRENT_SCHEMA_VERSION is a no-op."""
    conn = open_store()
    migrate(conn, target_version=CURRENT_SCHEMA_VERSION)
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert int(row[0]) == CURRENT_SCHEMA_VERSION
    conn.close()


def test_ensure_schema_on_fresh_db(tmp_path):
    """ensure_schema() on a brand-new (empty) connection creates the schema."""
    db_path = tmp_path / "fresh.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert row is not None
    assert int(row[0]) == 1
    conn.close()
