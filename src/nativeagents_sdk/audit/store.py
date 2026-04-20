"""SQLite audit store: open, write, read events with hash chain integrity."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from nativeagents_sdk.errors import AuditStoreError
from nativeagents_sdk.schema.audit import AuditEvent

if TYPE_CHECKING:
    from collections.abc import Iterator

# Path to the DDL file (relative to this module)
_DDL_PATH = Path(__file__).parent / "ddl.sql"


def _load_ddl() -> str:
    """Read the canonical DDL from ddl.sql."""
    return _DDL_PATH.read_text(encoding="utf-8")


def open_store(path: Path | None = None) -> sqlite3.Connection:
    """Open (or create) the SQLite audit database.

    Args:
        path: Path to the database file. If None, uses paths.audit_db_path().

    Returns:
        An open sqlite3.Connection configured for the audit store.

    Raises:
        AuditStoreError: If the database cannot be opened or created.
    """
    if path is None:
        from nativeagents_sdk.paths import audit_db_path, ensure_dir

        p = audit_db_path()
        ensure_dir(p.parent)
        path = p

    try:
        conn = sqlite3.connect(str(path), check_same_thread=False)
        # Restrict permissions to owner-only (spec §3.2 and §6.1 require 0600)
        path.chmod(0o600)
    except (sqlite3.Error, OSError) as exc:
        raise AuditStoreError(f"Cannot open audit database at {path}: {exc}") from exc

    # Configure connection
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")

        # Apply schema (idempotent: all CREATE TABLE IF NOT EXISTS)
        from nativeagents_sdk.audit.migrations import ensure_schema

        ensure_schema(conn)
    except sqlite3.Error as exc:
        conn.close()
        raise AuditStoreError(f"Failed to initialize audit database {path}: {exc}") from exc

    return conn


def _canonical_json(obj: object) -> str:
    """Produce canonical JSON: sorted keys, no whitespace, UTF-8 safe."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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
    """Compute the SHA-256 hash for a new audit row.

    The hash input is canonical JSON of a dict with exactly these keys
    (sorted alphabetically):
        captured_at, event_type, payload_json, plugin_name, prev_hash,
        sequence, session_id, timestamp

    prev_hash=None serializes as JSON null.
    """
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
    canonical = _canonical_json(hash_input)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_last_hash(conn: sqlite3.Connection, session_id: str) -> tuple[str | None, int]:
    """Return (last_row_hash, last_sequence) for a session.

    Returns (None, 0) if no rows exist for the session yet.
    """
    row = conn.execute(
        "SELECT row_hash, sequence FROM events WHERE session_id = ? ORDER BY sequence DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    if row is None:
        return None, 0
    return row["row_hash"], row["sequence"]


_MAX_SEQUENCE_RETRIES = 10


def write_event(conn: sqlite3.Connection, event: AuditEvent) -> str:
    """Insert an audit event into the store, maintaining the hash chain.

    Args:
        conn: Open connection from open_store().
        event: AuditEvent to write (sequence/prev_hash/row_hash will be set).

    Returns:
        The row_hash of the newly inserted row.

    Raises:
        AuditStoreError: On database write failure.
    """
    now = datetime.now(UTC)
    captured_at = event.captured_at if event.captured_at is not None else now

    timestamp_str = _dt_to_iso(event.timestamp)
    captured_at_str = _dt_to_iso(captured_at)
    payload_json = _canonical_json(event.payload)

    sequence = 0
    prev_hash: str | None = None
    row_hash = ""

    for attempt in range(_MAX_SEQUENCE_RETRIES):
        try:
            with conn:  # transaction: BEGIN / COMMIT or ROLLBACK
                prev_hash, last_seq = get_last_hash(conn, event.session_id)
                sequence = last_seq + 1

                row_hash = _compute_row_hash(
                    session_id=event.session_id,
                    sequence=sequence,
                    event_type=event.event_type,
                    plugin_name=event.plugin_name,
                    payload_json=payload_json,
                    timestamp=timestamp_str,
                    captured_at=captured_at_str,
                    prev_hash=prev_hash,
                )

                conn.execute(
                    """
                    INSERT INTO events (
                        session_id, sequence, event_type, plugin_name,
                        payload_json, payload_bytes,
                        timestamp, captured_at,
                        prev_hash, row_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.session_id,
                        sequence,
                        event.event_type,
                        event.plugin_name,
                        payload_json,
                        len(payload_json.encode("utf-8")),
                        timestamp_str,
                        captured_at_str,
                        prev_hash,
                        row_hash,
                    ),
                )
            break  # success — exit retry loop
        except sqlite3.IntegrityError:
            # Sequence collision from concurrent writers — re-read and retry
            if attempt == _MAX_SEQUENCE_RETRIES - 1:
                msg = f"sequence conflict after {_MAX_SEQUENCE_RETRIES} retries"
                raise AuditStoreError(f"Failed to write audit event: {msg}") from None
        except sqlite3.Error as exc:
            raise AuditStoreError(f"Failed to write audit event: {exc}") from exc

    # Update event in-place for caller convenience
    event.sequence = sequence
    event.prev_hash = prev_hash
    event.row_hash = row_hash
    event.captured_at = captured_at

    return row_hash


def read_events(
    conn: sqlite3.Connection,
    session_id: str,
    since_sequence: int = 0,
) -> Iterator[AuditEvent]:
    """Iterate over audit events for a session, in sequence order.

    Args:
        conn: Open connection from open_store().
        session_id: Session to read events for.
        since_sequence: Only return events with sequence > this value.

    Yields:
        AuditEvent instances in ascending sequence order.
    """
    cursor = conn.execute(
        """
        SELECT session_id, sequence, event_type, plugin_name,
               payload_json, timestamp, captured_at,
               prev_hash, row_hash
        FROM events
        WHERE session_id = ? AND sequence > ?
        ORDER BY sequence ASC
        """,
        (session_id, since_sequence),
    )
    for row in cursor:
        payload: object = json.loads(row["payload_json"])
        if not isinstance(payload, dict):
            payload = {}
        yield AuditEvent(
            session_id=row["session_id"],
            event_type=row["event_type"],
            plugin_name=row["plugin_name"],
            payload=payload,
            timestamp=_parse_iso(row["timestamp"]),
            captured_at=_parse_iso(row["captured_at"]),
            sequence=row["sequence"],
            prev_hash=row["prev_hash"],
            row_hash=row["row_hash"],
        )


def _dt_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO-8601 UTC string."""
    if dt.tzinfo is None:
        # Treat naive datetimes as UTC
        dt = dt.replace(tzinfo=UTC)
    # Normalise to UTC
    dt_utc = dt.astimezone(UTC)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _parse_iso(s: str) -> datetime:
    """Parse an ISO-8601 UTC string back to a timezone-aware datetime."""
    # Handle the Z suffix
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
