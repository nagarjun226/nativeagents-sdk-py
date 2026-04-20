"""Audit store: append-only SQLite event log with SHA-256 hash chain."""

from nativeagents_sdk.audit.integrity import VerificationReport, verify_integrity
from nativeagents_sdk.audit.store import get_last_hash, open_store, read_events, write_event

__all__ = [
    "open_store",
    "write_event",
    "read_events",
    "get_last_hash",
    "verify_integrity",
    "VerificationReport",
]
