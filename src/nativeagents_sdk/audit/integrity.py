"""Hash chain integrity verification for the audit store."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


def _compute_row_hash(
    session_id: str,
    sequence: int,
    event_type: str,
    plugin_name: str,
    payload_json: str,
    timestamp: str,
    captured_at: str,
    prev_hash: str | None,
) -> str:
    """Recompute the expected row_hash for a stored row."""
    hash_input: dict[str, object] = {
        "captured_at": captured_at,
        "event_type": event_type,
        "payload_json": payload_json,
        "plugin_name": plugin_name,
        "prev_hash": prev_hash,
        "sequence": sequence,
        "session_id": session_id,
        "timestamp": timestamp,
    }
    canonical = json.dumps(hash_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class VerificationReport:
    """Result of verify_integrity().

    Attributes:
        sessions_verified: Number of sessions that were checked.
        breaks: List of dicts describing each integrity break found.
            Each dict has: session_id, sequence, kind, details.
    """

    sessions_verified: int = 0
    breaks: list[dict[str, object]] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True if no breaks were found."""
        return len(self.breaks) == 0


def verify_integrity(
    conn: sqlite3.Connection,
    session_id: str | None = None,
) -> VerificationReport:
    """Verify the hash chain integrity of the audit store.

    For each session (or the specified session), iterates all rows in
    sequence order and:
    1. Recomputes the row_hash from stored fields.
    2. Compares to the stored row_hash.
    3. Checks that prev_hash matches the previous row's row_hash.
    4. Checks for sequence gaps.

    Args:
        conn: Open connection from open_store().
        session_id: If provided, only verify this session.
                    If None, verify all sessions.

    Returns:
        VerificationReport with details of any breaks found.
    """
    report = VerificationReport()

    if session_id is not None:
        sessions = [session_id]
    else:
        rows = conn.execute("SELECT DISTINCT session_id FROM events ORDER BY session_id").fetchall()
        sessions = [r[0] for r in rows]

    for sid in sessions:
        report.sessions_verified += 1
        _verify_session(conn, sid, report)

    return report


def _verify_session(
    conn: sqlite3.Connection,
    session_id: str,
    report: VerificationReport,
) -> None:
    """Verify a single session's hash chain, appending breaks to report."""
    rows = conn.execute(
        """
        SELECT session_id, sequence, event_type, plugin_name,
               payload_json, timestamp, captured_at,
               prev_hash, row_hash
        FROM events
        WHERE session_id = ?
        ORDER BY sequence ASC
        """,
        (session_id,),
    ).fetchall()

    if not rows:
        return

    prev_row_hash: str | None = None
    expected_sequence = 1

    for row in rows:
        seq = row["sequence"]

        # Check for sequence gap
        if seq != expected_sequence:
            report.breaks.append(
                {
                    "session_id": session_id,
                    "sequence": seq,
                    "kind": "sequence_gap",
                    "details": f"Expected sequence {expected_sequence}, got {seq}",
                }
            )
            # Skip to next expected based on what we actually got
            expected_sequence = seq + 1
        else:
            expected_sequence = seq + 1

        # Verify prev_hash link
        stored_prev_hash: str | None = row["prev_hash"]
        if seq == 1:
            if stored_prev_hash is not None:
                report.breaks.append(
                    {
                        "session_id": session_id,
                        "sequence": seq,
                        "kind": "bad_prev_hash",
                        "details": (
                            f"First row should have prev_hash=NULL, got {stored_prev_hash!r}"
                        ),
                    }
                )
        else:
            if stored_prev_hash != prev_row_hash:
                report.breaks.append(
                    {
                        "session_id": session_id,
                        "sequence": seq,
                        "kind": "bad_prev_hash",
                        "details": (
                            f"prev_hash mismatch: stored={stored_prev_hash!r}, "
                            f"expected={prev_row_hash!r}"
                        ),
                    }
                )

        # Verify row_hash
        expected_hash = _compute_row_hash(
            session_id=row["session_id"],
            sequence=row["sequence"],
            event_type=row["event_type"],
            plugin_name=row["plugin_name"],
            payload_json=row["payload_json"],
            timestamp=row["timestamp"],
            captured_at=row["captured_at"],
            prev_hash=stored_prev_hash,
        )
        stored_row_hash: str = row["row_hash"]
        if stored_row_hash != expected_hash:
            report.breaks.append(
                {
                    "session_id": session_id,
                    "sequence": seq,
                    "kind": "bad_row_hash",
                    "details": (
                        f"row_hash mismatch: stored={stored_row_hash!r}, computed={expected_hash!r}"
                    ),
                }
            )

        prev_row_hash = stored_row_hash
