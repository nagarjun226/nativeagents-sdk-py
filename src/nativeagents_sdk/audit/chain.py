"""Hash chain primitives for audit stores.

Plugins that maintain their own hash-chained event tables (e.g. agentaudit)
import ``compute_row_hash`` and define a ``ChainSpec`` describing which
fields participate in their hash.  The SDK's internal audit store uses
``SDK_CHAIN_SPEC``; plugins may declare a different spec without touching
the SDK's own chain.

Usage (plugin-side)::

    from nativeagents_sdk.audit.chain import ChainSpec, compute_row_hash

    MY_SPEC = ChainSpec(
        fields=("event_id", "session_id", "sequence",
                "event_type", "source", "payload_sha256",
                "prev_event_hash"),
    )

    row_hash = compute_row_hash(
        {
            "event_id": eid,
            "session_id": sid,
            "sequence": seq,
            "event_type": etype,
            "source": src,
            "payload_sha256": hashlib.sha256(payload_json.encode()).hexdigest(),
            "prev_event_hash": prev,
        },
        spec=MY_SPEC,
    )
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ChainSpec:
    """Specification for row hashing in a plugin's hash chain.

    Attributes:
        fields: Ordered tuple of field names whose values are pulled from
            the ``row_fields`` dict passed to ``compute_row_hash``.
            The values are serialised into canonical JSON (sort_keys=True)
            before hashing, so field order here does NOT affect the hash
            (JSON keys are always sorted); it only determines which keys are
            selected from the caller's dict.
    """

    fields: tuple[str, ...]


def compute_row_hash(row_fields: dict[str, object], *, spec: ChainSpec) -> str:
    """Compute the SHA-256 hash for one row in a hash chain.

    Args:
        row_fields: Dict containing at least the keys named in ``spec.fields``.
            Extra keys are silently ignored.  Values must be JSON-serialisable.
        spec: Which fields to include.  See ``ChainSpec``.

    Returns:
        64-character lowercase hex SHA-256 digest.

    Raises:
        KeyError: If a field named in ``spec.fields`` is absent from
            ``row_fields``.
        TypeError: If any selected value is not JSON-serialisable.
    """
    input_dict = {name: row_fields[name] for name in spec.fields}
    canonical = json.dumps(input_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Built-in spec: matches the SDK's own audit store (sdk.audit.store)
# ---------------------------------------------------------------------------

SDK_CHAIN_SPEC: ChainSpec = ChainSpec(
    fields=(
        "captured_at",
        "event_type",
        "payload_json",
        "plugin_name",
        "prev_hash",
        "sequence",
        "session_id",
        "timestamp",
    ),
)
"""ChainSpec used by the SDK's shared audit store (``sdk.audit.write_event``).

Hash input fields (sorted by JSON key):
    captured_at   — ISO-8601 UTC string of write time
    event_type    — event name string
    payload_json  — canonical JSON of the full payload (inline, not digested)
    plugin_name   — plugin that wrote the event
    prev_hash     — previous row's hash (None → JSON null for sequence=1)
    sequence      — per-session integer starting at 1
    session_id    — Claude Code session identifier
    timestamp     — ISO-8601 UTC string of occurrence time
"""
