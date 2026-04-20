"""Tests for the audit store (open_store, write_event, read_events)."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from nativeagents_sdk.audit.store import (
    get_last_hash,
    open_store,
    read_events,
    write_event,
)
from nativeagents_sdk.schema.audit import AuditEvent

_VECTORS_FILE = Path(__file__).parent / "fixtures" / "hash_chain_vectors.json"


def make_event(
    session_id: str = "test-session-001",
    event_type: str = "test.event",
    plugin_name: str = "test-plugin",
    payload: dict | None = None,
) -> AuditEvent:
    return AuditEvent(
        session_id=session_id,
        event_type=event_type,
        plugin_name=plugin_name,
        payload=payload or {},
        timestamp=datetime.now(UTC),
    )


def test_open_store_creates_db(isolated_home):
    """open_store() creates the database file."""
    from nativeagents_sdk.paths import audit_db_path

    conn = open_store()
    assert audit_db_path().exists()
    conn.close()


def test_open_store_idempotent(isolated_home):
    """open_store() can be called multiple times on the same DB."""
    conn1 = open_store()
    conn1.close()
    conn2 = open_store()
    conn2.close()


def test_write_single_event(isolated_home):
    """write_event() inserts a row and returns a hash."""
    conn = open_store()
    event = make_event()
    row_hash = write_event(conn, event)
    assert isinstance(row_hash, str)
    assert len(row_hash) == 64  # SHA-256 hex
    assert event.sequence == 1
    assert event.prev_hash is None
    assert event.row_hash == row_hash
    conn.close()


def test_write_multiple_events_sequence(isolated_home):
    """Multiple events for a session get sequential sequence numbers."""
    conn = open_store()
    session_id = "seq-test-session"
    for i in range(5):
        evt = make_event(session_id=session_id, payload={"i": i})
        write_event(conn, evt)
        assert evt.sequence == i + 1
    conn.close()


def test_write_events_hash_chain(isolated_home):
    """Each event's prev_hash matches the previous event's row_hash."""
    conn = open_store()
    session_id = "chain-test"
    events = [make_event(session_id=session_id, payload={"n": n}) for n in range(3)]
    for evt in events:
        write_event(conn, evt)

    assert events[0].prev_hash is None
    assert events[1].prev_hash == events[0].row_hash
    assert events[2].prev_hash == events[1].row_hash
    conn.close()


def test_read_events(isolated_home):
    """read_events() returns all events for a session."""
    conn = open_store()
    session_id = "read-test"
    written = []
    for i in range(3):
        evt = make_event(session_id=session_id, payload={"i": i})
        write_event(conn, evt)
        written.append(evt)

    read = list(read_events(conn, session_id))
    assert len(read) == 3
    for r, w in zip(read, written, strict=True):
        assert r.sequence == w.sequence
        assert r.row_hash == w.row_hash
        assert r.payload == w.payload
    conn.close()


def test_read_events_since_sequence(isolated_home):
    """read_events() with since_sequence filters correctly."""
    conn = open_store()
    session_id = "since-test"
    for _i in range(5):
        write_event(conn, make_event(session_id=session_id))

    # Read only events 3, 4, 5
    events = list(read_events(conn, session_id, since_sequence=2))
    assert len(events) == 3
    assert events[0].sequence == 3
    conn.close()


def test_get_last_hash_empty(isolated_home):
    """get_last_hash() returns (None, 0) for a session with no events."""
    conn = open_store()
    last_hash, last_seq = get_last_hash(conn, "nonexistent-session")
    assert last_hash is None
    assert last_seq == 0
    conn.close()


def test_get_last_hash_after_writes(isolated_home):
    """get_last_hash() returns correct values after writes."""
    conn = open_store()
    session_id = "hash-test"
    evt1 = make_event(session_id=session_id)
    write_event(conn, evt1)
    evt2 = make_event(session_id=session_id)
    write_event(conn, evt2)

    last_hash, last_seq = get_last_hash(conn, session_id)
    assert last_hash == evt2.row_hash
    assert last_seq == 2
    conn.close()


def test_multiple_sessions_independent(isolated_home):
    """Events in different sessions don't interfere."""
    conn = open_store()
    for sid in ["session-A", "session-B"]:
        for _ in range(3):
            write_event(conn, make_event(session_id=sid))

    events_a = list(read_events(conn, "session-A"))
    events_b = list(read_events(conn, "session-B"))

    # Each session has its own chain starting at 1
    assert events_a[0].prev_hash is None
    assert events_b[0].prev_hash is None
    assert events_a[0].sequence == 1
    assert events_b[0].sequence == 1
    conn.close()


def test_concurrent_writers(isolated_home):
    """Multiple threads can write events concurrently without corruption."""
    conn = open_store()
    n_threads = 5
    n_events_per_thread = 20
    errors = []

    def write_n_events(session_suffix: str) -> None:
        thread_conn = open_store()
        try:
            sid = f"thread-{session_suffix}"
            for _ in range(n_events_per_thread):
                evt = make_event(session_id=sid)
                write_event(thread_conn, evt)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=write_n_events, args=(str(i),)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors in threads: {errors}"

    # Verify each session has the right number of events
    for i in range(n_threads):
        events = list(read_events(conn, f"thread-{i}"))
        assert len(events) == n_events_per_thread
    conn.close()


def test_write_event_with_timestamp(isolated_home):
    """write_event() preserves the provided timestamp."""
    conn = open_store()
    ts = datetime(2026, 4, 19, 14, 30, 0, tzinfo=UTC)
    evt = AuditEvent(
        session_id="ts-test",
        event_type="test.ts",
        plugin_name="test",
        payload={},
        timestamp=ts,
    )
    write_event(conn, evt)

    read = list(read_events(conn, "ts-test"))
    assert read[0].timestamp.year == 2026
    assert read[0].timestamp.month == 4
    assert read[0].timestamp.day == 19
    conn.close()


def test_hash_chain_vectors():
    """Hash canonicalization matches the known-good test vectors in fixtures."""
    vectors = json.loads(_VECTORS_FILE.read_text(encoding="utf-8"))
    for vec in vectors:
        inp = vec["input"]
        canonical = json.dumps(inp, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert actual == vec["expected_hash"], (
            f"Vector {vec['description']!r}: expected {vec['expected_hash']!r}, got {actual!r}"
        )


def test_audit_db_mode_0600(isolated_home):
    """audit.db is created with mode 0600 (owner read/write only)."""
    import stat

    from nativeagents_sdk.paths import audit_db_path

    conn = open_store(audit_db_path())
    conn.close()

    db = audit_db_path()
    assert db.exists()
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"
