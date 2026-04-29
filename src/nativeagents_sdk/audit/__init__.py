"""Audit store: append-only SQLite event log with SHA-256 hash chain."""

from nativeagents_sdk.audit.chain import SDK_CHAIN_SPEC, ChainSpec, compute_row_hash
from nativeagents_sdk.audit.integrity import VerificationReport, verify_integrity
from nativeagents_sdk.audit.store import get_last_hash, open_store, read_events, write_event

__all__ = [
    "open_store",
    "write_event",
    "read_events",
    "get_last_hash",
    "verify_integrity",
    "VerificationReport",
    # chain primitives (v0.2)
    "ChainSpec",
    "SDK_CHAIN_SPEC",
    "compute_row_hash",
]
