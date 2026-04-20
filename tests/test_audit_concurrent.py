"""Concurrent-write tests for the audit store."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

from nativeagents_sdk.audit.integrity import verify_integrity
from nativeagents_sdk.audit.store import open_store, write_event
from nativeagents_sdk.schema.audit import AuditEvent


def _make_event(session_id: str, plugin_name: str = "test-plugin") -> AuditEvent:
    return AuditEvent(
        session_id=session_id,
        event_type="test.event",
        plugin_name=plugin_name,
        payload={"x": 1},
        timestamp=datetime.now(UTC),
    )


def test_concurrent_threads_same_session(isolated_home: tuple[Path, Path]) -> None:
    """Multiple threads writing to the same session produce a valid chain."""
    na_home, _ = isolated_home
    db_path = na_home / "audit.db"
    session_id = "concurrent-thread-session"
    n_threads = 4
    events_per_thread = 25

    # Pre-initialize DB so WAL mode is set before threads start
    init_conn = open_store(db_path)
    init_conn.close()

    errors: list[Exception] = []

    def writer_thread(thread_id: int) -> None:
        conn = open_store(db_path)
        try:
            for i in range(events_per_thread):
                event = AuditEvent(
                    session_id=session_id,
                    event_type="test.concurrent",
                    plugin_name=f"plugin-{thread_id}",
                    payload={"thread": thread_id, "i": i},
                    timestamp=datetime.now(UTC),
                )
                write_event(conn, event)
        except Exception as exc:
            errors.append(exc)
        finally:
            conn.close()

    threads = [threading.Thread(target=writer_thread, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"

    # Verify the chain
    conn = open_store(db_path)
    report = verify_integrity(conn, session_id=session_id)
    conn.close()

    assert report.is_clean, f"Chain broken: {report.breaks}"
    # Should have n_threads * events_per_thread rows
    conn2 = open_store(db_path)
    row = conn2.execute("SELECT COUNT(*) FROM events WHERE session_id=?", (session_id,)).fetchone()
    conn2.close()
    assert row[0] == n_threads * events_per_thread


def test_concurrent_threads_different_sessions(isolated_home: tuple[Path, Path]) -> None:
    """Multiple threads writing to different sessions, all chains verify."""
    na_home, _ = isolated_home
    db_path = na_home / "audit.db"
    # Pre-initialize DB
    init_conn = open_store(db_path)
    init_conn.close()
    n_threads = 4
    events_per_thread = 25
    errors: list[Exception] = []

    def writer(tid: int) -> None:
        conn = open_store(db_path)
        try:
            for i in range(events_per_thread):
                event = AuditEvent(
                    session_id=f"session-{tid}",
                    event_type="test.concurrent",
                    plugin_name="test-plugin",
                    payload={"i": i},
                    timestamp=datetime.now(UTC),
                )
                write_event(conn, event)
        except Exception as exc:
            errors.append(exc)
        finally:
            conn.close()

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors

    conn = open_store(db_path)
    for tid in range(n_threads):
        report = verify_integrity(conn, session_id=f"session-{tid}")
        assert report.is_clean, f"session-{tid} chain broken: {report.breaks}"
    conn.close()
