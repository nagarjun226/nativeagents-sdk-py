# Contract 03: Audit Schema

**Status**: Canonical  
**Last updated against spec version**: 0.1.0  
**Schema version**: 1  
**File**: `~/.nativeagents/audit.db` (SQLite, WAL mode)

## SQLite configuration

- Journal mode: WAL
- Synchronous: NORMAL
- foreign_keys: ON
- busy_timeout: 5000ms
- Mode: 0600

## Hash chain algorithm

For each new row in a session:

```python
hash_input = {
    "captured_at":  ...,   # ISO-8601 UTC string
    "event_type":   ...,
    "payload_json": ...,   # canonical JSON of payload
    "plugin_name":  ...,
    "prev_hash":    ...,   # None → null in JSON; sequence 1 only
    "sequence":     ...,   # per-session monotonic integer starting at 1
    "session_id":   ...,
    "timestamp":    ...,   # ISO-8601 UTC string
}
canonical = json.dumps(hash_input, sort_keys=True, separators=(',',':'), ensure_ascii=False)
row_hash = sha256(canonical.encode('utf-8')).hexdigest()
```

## Invariants

- `sequence` is per-session, starts at 1, strictly monotonic
- `prev_hash` is NULL for sequence=1, else equals the previous row's `row_hash`
- `row_hash` is always a 64-char SHA-256 hex string
- No UPDATE or DELETE on `events` table is permitted

## Plugin-specific chain specs (v0.2)

Plugins that maintain their own hash-chained event tables (e.g. `agentaudit-cc`)
may use a different set of hash fields, a different payload representation
(e.g. SHA-256 digest instead of inline JSON), or a different genesis sentinel.

The SDK exposes a primitive that supports this:

```python
from nativeagents_sdk.audit.chain import ChainSpec, compute_row_hash

MY_SPEC = ChainSpec(
    fields=("event_id", "session_id", "sequence",
            "event_type", "source", "payload_sha256",
            "prev_event_hash"),
)

row_hash = compute_row_hash(row_fields_dict, spec=MY_SPEC)
```

`SDK_CHAIN_SPEC` describes the shared audit store's algorithm (8 fields,
inline `payload_json`, `prev_hash=None` for sequence 1).

Each plugin defines its own `ChainSpec` locally.  The SDK does not validate
or interpret plugin-defined specs — it only provides the `compute_row_hash`
primitive so plugins do not need to reimplement SHA-256 canonical hashing.

**Two-store model:** the SDK's shared `audit.db` uses `SDK_CHAIN_SPEC`.
Plugins with richer event schemas (e.g. agentaudit's `events` table with
`source`, `cwd`, `origin_json`) maintain a separate store using their own
spec.  Both stores use the same `compute_row_hash` function; neither store's
chain is compatible with the other's.

## See also

`src/nativeagents_sdk/audit/ddl.sql` — canonical DDL  
`src/nativeagents_sdk/audit/chain.py` — `ChainSpec`, `compute_row_hash`, `SDK_CHAIN_SPEC`
