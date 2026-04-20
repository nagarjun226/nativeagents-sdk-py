"""Property-based tests for the audit hash chain using Hypothesis."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from nativeagents_sdk.audit.integrity import verify_integrity
from nativeagents_sdk.audit.store import open_store, write_event
from nativeagents_sdk.schema.audit import AuditEvent

_PLUGIN_NAMES = st.sampled_from(["plugin-a", "plugin-b", "test-plugin"])
_SESSION_IDS = st.from_regex(r"[a-zA-Z0-9_\-]{1,32}", fullmatch=True)
_EVENT_TYPES = st.sampled_from(["PreToolUse", "PostToolUse", "SessionStart", "my-plugin.custom"])
_PAYLOADS = st.fixed_dictionaries(
    {
        "key": st.text(max_size=20),
        "num": st.integers(min_value=0, max_value=999),
    }
)


@given(
    session_id=_SESSION_IDS,
    num_events=st.integers(min_value=1, max_value=30),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_chain_always_verifies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_id: str,
    num_events: int,
) -> None:
    """Any sequence of valid events produces a verifiable chain."""
    # We need our own isolated home for each hypothesis example
    na_home = tmp_path / "na_home"
    na_home.mkdir(exist_ok=True)
    monkeypatch.setenv("NATIVEAGENTS_HOME", str(na_home))

    db_path = na_home / "audit.db"
    conn = open_store(db_path)

    for i in range(num_events):
        event = AuditEvent(
            session_id=session_id,
            event_type="test.hypothesis",
            plugin_name="test-plugin",
            payload={"i": i},
            timestamp=datetime.now(UTC),
        )
        write_event(conn, event)

    report = verify_integrity(conn, session_id=session_id)
    conn.close()

    assert report.is_clean, f"Chain broken with {num_events} events: {report.breaks}"


@given(
    session_id=_SESSION_IDS,
    num_events=st.integers(min_value=2, max_value=20),
    tamper_idx=st.integers(min_value=0, max_value=19),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_single_byte_tamper_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_id: str,
    num_events: int,
    tamper_idx: int,
) -> None:
    """Tampering any row's payload breaks verification."""
    na_home = tmp_path / "na_home2"
    na_home.mkdir(exist_ok=True)
    monkeypatch.setenv("NATIVEAGENTS_HOME", str(na_home))

    db_path = na_home / "audit.db"
    conn = open_store(db_path)

    for i in range(num_events):
        event = AuditEvent(
            session_id=session_id,
            event_type="test.tamper",
            plugin_name="test-plugin",
            payload={"i": i},
            timestamp=datetime.now(UTC),
        )
        write_event(conn, event)

    # Tamper a row: pick valid index within range
    actual_idx = (tamper_idx % num_events) + 1  # sequences start at 1
    conn.execute(
        "UPDATE events SET payload_json = ? WHERE session_id = ? AND sequence = ?",
        ('{"tampered": true}', session_id, actual_idx),
    )
    conn.commit()

    report = verify_integrity(conn, session_id=session_id)
    conn.close()

    assert not report.is_clean, "Tamper was not detected!"
    assert len(report.breaks) > 0
