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

## See also

`src/nativeagents_sdk/audit/ddl.sql` — canonical DDL
