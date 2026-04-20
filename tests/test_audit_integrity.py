"""Tests for audit hash chain integrity verification."""

from __future__ import annotations

from datetime import UTC, datetime

from nativeagents_sdk.audit.integrity import verify_integrity
from nativeagents_sdk.audit.store import open_store, write_event
from nativeagents_sdk.schema.audit import AuditEvent


def make_event(session_id: str = "test-001") -> AuditEvent:
    return AuditEvent(
        session_id=session_id,
        event_type="test.event",
        plugin_name="test-plugin",
        payload={"key": "value"},
        timestamp=datetime.now(UTC),
    )


def test_empty_db_is_clean(isolated_home):
    """Empty database verifies cleanly."""
    conn = open_store()
    report = verify_integrity(conn)
    assert report.is_clean
    assert report.sessions_verified == 0
    conn.close()


def test_clean_chain_verifies(isolated_home):
    """A chain written by write_event() verifies cleanly."""
    conn = open_store()
    session_id = "clean-session"
    for _ in range(10):
        write_event(conn, make_event(session_id=session_id))

    report = verify_integrity(conn, session_id=session_id)
    assert report.is_clean
    assert report.sessions_verified == 1
    conn.close()


def test_tampered_payload_detected(isolated_home):
    """Tampering with a row's payload_json breaks the chain."""
    conn = open_store()
    session_id = "tamper-payload"
    for _ in range(3):
        write_event(conn, make_event(session_id=session_id))

    # Directly tamper with row 2's payload
    conn.execute(
        "UPDATE events SET payload_json = ? WHERE session_id = ? AND sequence = 2",
        ('{"tampered": true}', session_id),
    )
    conn.commit()

    report = verify_integrity(conn, session_id=session_id)
    assert not report.is_clean
    # Row 2's hash doesn't match, and row 3's prev_hash doesn't match
    broken_seqs = {b["sequence"] for b in report.breaks}
    assert 2 in broken_seqs
    conn.close()


def test_tampered_row_hash_detected(isolated_home):
    """Directly changing a row_hash is detected."""
    conn = open_store()
    session_id = "tamper-hash"
    for _ in range(3):
        write_event(conn, make_event(session_id=session_id))

    # Tamper with row 1's row_hash
    fake_hash = "a" * 64
    conn.execute(
        "UPDATE events SET row_hash = ? WHERE session_id = ? AND sequence = 1",
        (fake_hash, session_id),
    )
    conn.commit()

    report = verify_integrity(conn, session_id=session_id)
    assert not report.is_clean
    broken_seqs = {b["sequence"] for b in report.breaks}
    assert 1 in broken_seqs
    conn.close()


def test_all_sessions_verified(isolated_home):
    """verify_integrity(session_id=None) checks all sessions."""
    conn = open_store()
    for sid in ["session-1", "session-2", "session-3"]:
        for _ in range(2):
            write_event(conn, make_event(session_id=sid))

    report = verify_integrity(conn)
    assert report.is_clean
    assert report.sessions_verified == 3
    conn.close()


def test_specific_session_verified(isolated_home):
    """verify_integrity(session_id=X) only checks session X."""
    conn = open_store()
    for sid in ["session-a", "session-b"]:
        for _ in range(3):
            write_event(conn, make_event(session_id=sid))

    # Tamper with session-a only
    conn.execute(
        "UPDATE events SET payload_json = ? WHERE session_id = 'session-a' AND sequence = 1",
        ('{"tampered": true}',),
    )
    conn.commit()

    report_a = verify_integrity(conn, session_id="session-a")
    assert not report_a.is_clean

    report_b = verify_integrity(conn, session_id="session-b")
    assert report_b.is_clean
    conn.close()


def test_verification_report_structure(isolated_home):
    """VerificationReport has expected fields."""
    conn = open_store()
    report = verify_integrity(conn)
    assert hasattr(report, "sessions_verified")
    assert hasattr(report, "breaks")
    assert hasattr(report, "is_clean")
    assert isinstance(report.breaks, list)
    conn.close()
