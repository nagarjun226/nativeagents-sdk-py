"""Tests for nativeagents_sdk.audit.chain."""

from __future__ import annotations

import hashlib
import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nativeagents_sdk.audit.chain import SDK_CHAIN_SPEC, ChainSpec, compute_row_hash

# ---------------------------------------------------------------------------
# ChainSpec dataclass
# ---------------------------------------------------------------------------


def test_chain_spec_is_frozen() -> None:
    spec = ChainSpec(fields=("a", "b"))
    with pytest.raises((AttributeError, TypeError)):
        spec.fields = ("x",)  # type: ignore[misc]


def test_chain_spec_equality() -> None:
    a = ChainSpec(fields=("x", "y"))
    b = ChainSpec(fields=("x", "y"))
    assert a == b


def test_chain_spec_hashable() -> None:
    spec = ChainSpec(fields=("a",))
    assert hash(spec) == hash(spec)
    s: set[ChainSpec] = {spec}
    assert spec in s


# ---------------------------------------------------------------------------
# compute_row_hash — basic correctness
# ---------------------------------------------------------------------------


def _make_sdk_fields(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "captured_at": "2026-04-19T12:00:00.000000Z",
        "event_type": "PreToolUse",
        "payload_json": '{"tool_name":"Bash"}',
        "plugin_name": "agentaudit",
        "prev_hash": None,
        "sequence": 1,
        "session_id": "abc123",
        "timestamp": "2026-04-19T12:00:00.000000Z",
    }
    base.update(overrides)
    return base


def test_compute_row_hash_returns_64_char_hex() -> None:
    h = compute_row_hash(_make_sdk_fields(), spec=SDK_CHAIN_SPEC)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_row_hash_deterministic() -> None:
    fields = _make_sdk_fields()
    h1 = compute_row_hash(fields, spec=SDK_CHAIN_SPEC)
    h2 = compute_row_hash(fields, spec=SDK_CHAIN_SPEC)
    assert h1 == h2


def test_compute_row_hash_matches_manual() -> None:
    """Verify the hash matches a hand-computed reference."""
    fields = _make_sdk_fields()
    selected = {name: fields[name] for name in SDK_CHAIN_SPEC.fields}
    canonical = json.dumps(selected, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert compute_row_hash(fields, spec=SDK_CHAIN_SPEC) == expected


def test_compute_row_hash_sensitive_to_each_field() -> None:
    """Changing any single field must change the hash."""
    base_fields = _make_sdk_fields()
    base_hash = compute_row_hash(base_fields, spec=SDK_CHAIN_SPEC)

    mutations: list[dict[str, object]] = [
        {"session_id": "different"},
        {"sequence": 2},
        {"event_type": "PostToolUse"},
        {"plugin_name": "other-plugin"},
        {"payload_json": '{"tool_name":"Write"}'},
        {"timestamp": "2026-04-20T00:00:00.000000Z"},
        {"captured_at": "2026-04-20T00:00:00.000000Z"},
        {"prev_hash": "a" * 64},
    ]

    for mutation in mutations:
        mutated = {**base_fields, **mutation}
        assert compute_row_hash(mutated, spec=SDK_CHAIN_SPEC) != base_hash, (
            f"Hash unchanged after mutation: {mutation}"
        )


def test_compute_row_hash_extra_keys_ignored() -> None:
    """Extra keys in row_fields that are not in spec.fields must be ignored."""
    fields = _make_sdk_fields(extra_key="should_be_ignored")
    h_with_extra = compute_row_hash(fields, spec=SDK_CHAIN_SPEC)
    fields_no_extra = {k: v for k, v in fields.items() if k != "extra_key"}
    h_without = compute_row_hash(fields_no_extra, spec=SDK_CHAIN_SPEC)
    assert h_with_extra == h_without


def test_compute_row_hash_missing_field_raises() -> None:
    incomplete = {"session_id": "abc", "sequence": 1}
    with pytest.raises(KeyError):
        compute_row_hash(incomplete, spec=SDK_CHAIN_SPEC)


# ---------------------------------------------------------------------------
# compute_row_hash — custom spec (agentaudit-style)
# ---------------------------------------------------------------------------

AGENTAUDIT_SPEC = ChainSpec(
    fields=(
        "event_id",
        "session_id",
        "sequence",
        "event_type",
        "source",
        "payload_sha256",
        "prev_event_hash",
    ),
)


def _agentaudit_fields(payload_json: str = '{"tool_name":"Bash"}') -> dict[str, object]:
    return {
        "event_id": "d1e2f3a4-0000-0000-0000-000000000001",
        "session_id": "sess-001",
        "sequence": 1,
        "event_type": "PreToolUse",
        "source": "hook",
        "payload_sha256": hashlib.sha256(payload_json.encode()).hexdigest(),
        "prev_event_hash": "0" * 64,
    }


def test_agentaudit_spec_hash_64_hex() -> None:
    h = compute_row_hash(_agentaudit_fields(), spec=AGENTAUDIT_SPEC)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_agentaudit_spec_differs_from_sdk_spec() -> None:
    """The two specs should produce different hashes even from similar data."""
    sdk_fields = _make_sdk_fields()
    aa_fields = _agentaudit_fields()
    h_sdk = compute_row_hash(sdk_fields, spec=SDK_CHAIN_SPEC)
    h_aa = compute_row_hash(aa_fields, spec=AGENTAUDIT_SPEC)
    assert h_sdk != h_aa  # different algorithms → different hashes


def test_agentaudit_spec_payload_sha256_is_binding() -> None:
    """Changing payload (and thus payload_sha256) changes the hash."""
    fields1 = _agentaudit_fields('{"tool_name":"Bash"}')
    fields2 = _agentaudit_fields('{"tool_name":"Write"}')
    assert compute_row_hash(fields1, spec=AGENTAUDIT_SPEC) != compute_row_hash(
        fields2, spec=AGENTAUDIT_SPEC
    )


# ---------------------------------------------------------------------------
# SDK_CHAIN_SPEC constant — verify fields match contract doc
# ---------------------------------------------------------------------------


def test_sdk_chain_spec_fields() -> None:
    expected = frozenset(
        [
            "captured_at",
            "event_type",
            "payload_json",
            "plugin_name",
            "prev_hash",
            "sequence",
            "session_id",
            "timestamp",
        ]
    )
    assert frozenset(SDK_CHAIN_SPEC.fields) == expected


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


@given(
    session_id=st.text(min_size=1, max_size=50),
    sequence=st.integers(min_value=1, max_value=10_000),
    event_type=st.text(min_size=1, max_size=30),
    payload=st.text(max_size=200),
)
@settings(max_examples=200)
def test_hash_always_64_hex(session_id: str, sequence: int, event_type: str, payload: str) -> None:
    fields = _make_sdk_fields(
        session_id=session_id,
        sequence=sequence,
        event_type=event_type,
        payload_json=payload,
    )
    h = compute_row_hash(fields, spec=SDK_CHAIN_SPEC)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


@given(
    a=st.text(max_size=100),
    b=st.text(max_size=100),
)
@settings(max_examples=300)
def test_different_payloads_produce_different_hashes(a: str, b: str) -> None:
    if a == b:
        return
    ha = compute_row_hash(_make_sdk_fields(payload_json=a), spec=SDK_CHAIN_SPEC)
    hb = compute_row_hash(_make_sdk_fields(payload_json=b), spec=SDK_CHAIN_SPEC)
    assert ha != hb
