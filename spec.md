# nativeagents-sdk-py — Technical Specification

> This is the canonical technical contract. Every file format, schema, and API surface that plugins depend on is specified here. Changes to this document are breaking changes to the ecosystem.
>
> **Audience:** the Claude Code session implementing this SDK, and future third-party plugin authors.
>
> **Read `plan.md` first** for build sequencing and context.

---

## Table of contents

1. Scope and conformance levels
2. Global conventions
3. Canonical directory layout: `~/.nativeagents/`
4. Plugin namespacing rules
5. Plugin manifest: `plugin.toml`
6. Audit schema: SQLite + hash chain
7. Memory manifest: `manifest.json` + memory file frontmatter
8. Hook script contract
9. Hook dispatcher Python API
10. Spool format
11. Install registration: `~/.claude/settings.json` merge rules
12. Config file: `config.yaml`
13. CLI conventions
14. Error handling and exit codes
15. Versioning and schema evolution
16. Public Python API surface (what `nativeagents_sdk` exports)
17. Non-goals

---

## 1. Scope and conformance levels

A plugin may conform to the Native Agents SDK contract at one of three levels:

- **Core conformance (required).** Plugin ships a valid `plugin.toml`; obeys the directory layout; does not write outside its declared `owns_paths`; uses the hook script contract.
- **Audit conformance (required if `writes_audit_events = true`).** Plugin writes audit events to the shared `audit.db` using the SDK's `write_event` API (or an independent implementation that matches the spec in §6) with correct hash chaining.
- **Full conformance (recommended).** Plugin uses the SDK library for config, hooks, manifest, spool, and install. Runs `nativeagents-sdk validate-plugin` and passes the conformance harness.

Throughout this document: **MUST**, **SHOULD**, **MAY** carry RFC 2119 meanings.

---

## 2. Global conventions

### 2.1 Character encoding

All text files MUST be UTF-8. All JSON files MUST be UTF-8 without BOM.

### 2.2 Timestamps

All timestamps MUST be ISO-8601 with a timezone, UTC preferred (`2026-04-19T14:30:00Z`). Pydantic models use `datetime` with `tzinfo`.

### 2.3 Plugin names

Plugin names MUST match `^[a-z][a-z0-9-]{0,39}$`. That is: lowercase alphanumeric + hyphen, starting with a letter, 1–40 characters. Names are case-sensitive (but the regex restricts to lowercase).

Reserved names (MUST NOT be used by any plugin):

- `audit`, `memory`, `wiki`, `policies`, `plugins`, `spool`, `bin`, `sidecar`, `config`, `meta`, `system`

These are reserved for SDK-owned subdirectories under `~/.nativeagents/`.

### 2.4 Plugin namespaces

Each plugin is assigned a single namespace equal to its plugin name. All of the plugin's owned paths live under that namespace. A plugin MUST NOT write outside its namespace except to `audit.db` (shared, via SDK) and `spool/<plugin_name>/` (shared spool directory, per-plugin subdir).

### 2.5 Atomicity

Any file write that might be read by another process MUST be atomic:

1. Write to `<target>.tmp.<pid>.<random>`
2. `fsync` the file.
3. `os.replace(tmp, target)`.

The SDK provides a `paths.atomic_write(path, data)` helper; plugins SHOULD use it.

### 2.6 Path resolution

All on-disk paths are resolved relative to two roots:

- `NATIVEAGENTS_HOME` (default: `~/.nativeagents`, resolved via `Path.home()`)
- `CLAUDE_HOME` (default: `~/.claude`)

These are readable from env vars to support testing and sandboxed deployments. The SDK's `paths` module is the ONLY place these roots are resolved — no other module, and no plugin, should read `~/.nativeagents` directly.

### 2.7 Schema versions

Every on-disk file format in this spec carries an integer `schema_version` field. The current version for each format is defined in the relevant section. Readers MUST tolerate unknown trailing fields (forward compat) but MAY reject if `schema_version` is higher than they understand.

---

## 3. Canonical directory layout: `~/.nativeagents/`

```
~/.nativeagents/
├── config.yaml                      # global config; SDK-owned
├── audit.db                         # shared SQLite audit store; SDK-owned schema
├── audit.db-wal                     # SQLite WAL file; SDK-owned
├── audit.db-shm                     # SQLite shared-memory file; SDK-owned
├── meta.json                        # SDK-owned metadata (installed plugins list, versions)
│
├── memory/                          # memory plugin namespace
│   ├── manifest.json                # memory manifest (format in §7)
│   ├── core/                        # suggested category (not enforced)
│   │   ├── user.md
│   │   └── context.md
│   ├── relationship/
│   ├── projects/
│   ├── procedures/
│   ├── working/
│   └── reference/
│
├── wiki/                            # wiki plugin namespace
│   ├── graph.db                     # wiki-internal SQLite (wiki-owned, not audit)
│   ├── pages/                       # wiki markdown pages
│   ├── raw-inbox/                   # drop zone for admin seeds (wiki cron absorbs)
│   └── index.json                   # wiki-internal index
│
├── policies/                        # shared policy directory (SDK-owned dir, plugin-populated files)
│   ├── local/                       # user-authored policies
│   ├── pushed/                      # sidecar-pushed policies (future)
│   └── active/                      # symlinks or compiled view of currently-active rules
│
├── spool/                           # shared spool root; one subdir per plugin per kind
│   └── <plugin_name>/
│       └── <kind>/                  # e.g. "audit", "inbox", "outbound"
│
├── plugins/                         # third-party plugin state; one subdir per plugin
│   └── <plugin_name>/               # plugin-owned; SDK does not write here
│       ├── plugin.toml              # copied or symlinked here at install
│       ├── state.db                 # plugin-private state (optional)
│       ├── logs/                    # plugin logs
│       └── <whatever>
│
├── bin/                             # managed venv + CLI entry points (optional, SDK-helper)
│   ├── python3                      # symlink into the managed venv
│   ├── agentaudit
│   ├── agentmemory
│   ├── agentwiki
│   └── nativeagents
│
└── sidecar/                         # reserved for future paid sidecar; unused in OSS
```

### 3.1 Ownership rules

- **SDK-owned:** `config.yaml`, `audit.db` (schema + write coordination), `meta.json`, `policies/` (directory structure — plugins write files into it), `spool/` (directory structure — plugins write under `<plugin_name>/<kind>/`), `bin/` (if managed venv is used), `sidecar/`.
- **Plugin-owned:** `memory/` (agentmemory-cc), `wiki/` (agentwiki-cc), `plugins/<name>/` (any plugin).
- **Shared-write:** `audit.db` is shared but writes MUST go through the SDK's `write_event` API to preserve the hash chain.

### 3.2 Filesystem invariants

- All SDK-owned top-level directories MUST be created with mode `0700`.
- `audit.db` MUST be created with mode `0600`.
- Plugin-owned directories inherit the mode of `~/.nativeagents/plugins/`.

### 3.3 Cross-plugin visibility

A plugin MAY read any file under `~/.nativeagents/` (it's all local to the user). A plugin MUST NOT write outside its namespace or shared-write surfaces.

---

## 4. Plugin namespacing rules

1. A plugin's namespace is its `plugin.name`.
2. The plugin's state directory is `~/.nativeagents/plugins/<name>/`, EXCEPT for the three first-party plugins which have well-known namespaces:
   - `agentaudit` → `audit.db` (shared) + optional `~/.nativeagents/plugins/agentaudit/` for extra state.
   - `agentmemory` → `~/.nativeagents/memory/`.
   - `agentwiki` → `~/.nativeagents/wiki/`.

   These three are carve-outs declared via `plugin.toml` `well_known_namespace` field. Third-party plugins MUST NOT use the well-known namespaces and MUST use `plugins/<name>/`.

3. Plugins MAY declare additional paths they own via `owns_paths` in `plugin.toml`. Owned paths MUST be under the plugin's namespace (enforced at install time by the SDK).

4. Spool writes go to `~/.nativeagents/spool/<plugin_name>/<kind>/`. `kind` is plugin-defined but common kinds are:
   - `audit` — events queued for audit drain (SDK manages drain)
   - `inbox` — items to be consumed by the plugin
   - `outbound` — items to be consumed by the sidecar (future)

---

## 5. Plugin manifest: `plugin.toml`

Every plugin ships a `plugin.toml` at the root of its package. This file is the plugin's self-declaration to the ecosystem.

### 5.1 Schema

```toml
# plugin.toml — canonical form

schema_version = 1

[plugin]
# Required fields
name = "agentaudit"                  # MUST match §2.3 regex
version = "0.5.2"                    # SemVer
description = "Governance, observability, and audit for Claude Code agents"

# Optional fields
homepage = "https://github.com/nativeagents/agentaudit-cc"
license = "MIT"
authors = ["Native Agents <team@nativeagents.net>"]

# Well-known namespace carve-out — only for first-party plugins
# Third-party plugins MUST NOT set this.
well_known_namespace = "audit"       # one of: "audit", "memory", "wiki" (or absent)

# Hooks this plugin wants registered in ~/.claude/settings.json
# Each string MUST be a valid Claude Code hook event name.
hooks = [
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "PreCompact",
    "PostCompact",
    "Stop",
    "SubagentStop",
    "SessionEnd",
]

# Paths this plugin claims ownership of.
# Paths are relative to ~/.nativeagents/ unless absolute.
# Paths outside the plugin's namespace MUST NOT appear here except
# for well-known-namespaced plugins.
owns_paths = [
    "plugins/agentaudit/",
]

# Declares the plugin writes audit events. If true, the plugin MUST
# conform to §6 (audit schema + hash chain).
writes_audit_events = true

# Declares the plugin produces spool files for a sidecar to drain.
# Sidecar, when present, will tail these directories.
produces_spool_kinds = ["audit"]

# CLI entry point (for super-repo aggregation).
# Format: "module.path:callable"
cli_entry = "agentaudit.cli:app"

# Python module to execute via hook dispatcher.
hook_module = "agentaudit.hook"

# Minimum SDK version this plugin is compatible with.
min_sdk_version = "0.1.0"

# Maximum SDK version this plugin is compatible with (optional).
max_sdk_version = "1.0.0"

[plugin.requires]
# Other plugins this plugin depends on (by name). Optional.
# The SDK MAY warn if listed plugins are not installed; MUST NOT refuse to load.
optional = ["agentmemory"]           # "nice to have"
required = []                        # "refuse to load without"
```

### 5.2 Validation rules

- `schema_version` MUST be 1.
- `plugin.name` MUST match `^[a-z][a-z0-9-]{0,39}$`.
- `plugin.version` MUST be valid SemVer.
- `plugin.hooks` entries MUST each be a valid Claude Code hook event name (from the enum in §6.3).
- `plugin.owns_paths` entries MUST be within the plugin's namespace, UNLESS `well_known_namespace` is set to one of the carve-outs.
- `plugin.cli_entry` and `plugin.hook_module` MUST be importable Python references (the SDK does NOT verify this at load time — the plugin's own install script verifies).
- `plugin.min_sdk_version` and `plugin.max_sdk_version` MUST be valid SemVer if present.

### 5.3 Storage

At install time, the SDK copies (not symlinks) the plugin's `plugin.toml` to `~/.nativeagents/plugins/<name>/plugin.toml`. This allows plugin discovery without requiring the plugin's source tree to be present (e.g., if the plugin is installed in a venv).

For well-known-namespaced plugins, the copy goes to the well-known directory:

- agentaudit → `~/.nativeagents/plugins/agentaudit/plugin.toml` (created even though it's well-known)
- agentmemory → `~/.nativeagents/memory/plugin.toml`
- agentwiki → `~/.nativeagents/wiki/plugin.toml`

### 5.4 Discovery

The SDK's `plugin.discovery.discover_plugins()` scans:

- `~/.nativeagents/plugins/*/plugin.toml`
- `~/.nativeagents/memory/plugin.toml`
- `~/.nativeagents/wiki/plugin.toml`

Malformed files are logged to `~/.nativeagents/meta.log` and skipped. No exception escapes.

---

## 6. Audit schema: SQLite + hash chain

This is the most security-critical part of the SDK. Every decision here is driven by tamper evidence.

### 6.1 SQLite file

- Path: `~/.nativeagents/audit.db`.
- Mode: `0600`.
- Journal mode: `WAL`.
- Synchronous: `NORMAL` (good balance between durability and throughput; the hash chain provides additional integrity evidence beyond SQLite's own).
- `foreign_keys = ON`.
- `PRAGMA busy_timeout = 5000` (5s).

### 6.2 Schema DDL (version 1)

Paste this DDL into `src/nativeagents_sdk/audit/ddl.sql` verbatim. The SDK applies it when it detects a fresh database.

```sql
-- =====================================================================
-- Native Agents SDK — audit schema v1
-- =====================================================================
-- This schema is the contract between plugins, the SDK, and (eventually)
-- the Native Agents sidecar. Do NOT modify in place; use a migration.
-- =====================================================================

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Initial meta row: schema version.
-- Migrations update this value.
INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1');
INSERT OR IGNORE INTO meta (key, value) VALUES ('created_at', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));

-- ---------------------------------------------------------------------
-- events — the append-only audit log
-- ---------------------------------------------------------------------
-- Every observation any plugin records lands here.
-- Ordering within a session: strictly monotonic `sequence` starting at 1.
-- Ordering across sessions: by `timestamp` (observed) or `captured_at` (wall-clock at write).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    -- Row identity
    id               INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Event identity
    session_id       TEXT    NOT NULL,
    sequence         INTEGER NOT NULL,            -- per-session monotonic, starting at 1
    event_type       TEXT    NOT NULL,            -- e.g. "PreToolUse", or plugin-defined like "my-plugin.observation"
    plugin_name      TEXT    NOT NULL,            -- which plugin wrote this row

    -- Payload (opaque JSON, plugins own the shape for their own event_types)
    payload_json     TEXT    NOT NULL,            -- canonical JSON (UTF-8, sorted keys, no whitespace)
    payload_bytes    INTEGER NOT NULL,            -- len(payload_json) for quick stats

    -- Time
    timestamp        TEXT    NOT NULL,            -- ISO-8601 UTC — the EVENT's occurrence time
    captured_at      TEXT    NOT NULL,            -- ISO-8601 UTC — write time (may differ if spooled)

    -- Hash chain
    prev_hash        TEXT,                        -- SHA-256 hex of the previous row in this session's chain; NULL only for sequence=1
    row_hash         TEXT NOT NULL,               -- SHA-256 hex of (prev_hash || canonical_json(this_row_without_row_hash_field))

    -- Integrity constraints
    UNIQUE (session_id, sequence),
    CHECK (sequence >= 1),
    CHECK (length(row_hash) = 64),
    CHECK (prev_hash IS NULL OR length(prev_hash) = 64)
);

CREATE INDEX IF NOT EXISTS idx_events_session_seq ON events (session_id, sequence);
CREATE INDEX IF NOT EXISTS idx_events_event_type  ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_plugin      ON events (plugin_name);
CREATE INDEX IF NOT EXISTS idx_events_captured    ON events (captured_at);

-- ---------------------------------------------------------------------
-- sessions — lightweight session registry (optional denormalization)
-- ---------------------------------------------------------------------
-- Not part of the hash chain. Rebuilt from events on demand by plugins.
-- The SDK does NOT write here; agentaudit does via its projections layer.
-- The SDK creates the table for convenience but doesn't populate it.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    session_id       TEXT PRIMARY KEY,
    started_at       TEXT NOT NULL,
    ended_at         TEXT,
    agent_framework  TEXT NOT NULL DEFAULT 'claude-code',
    cwd              TEXT,
    extra_json       TEXT                          -- plugin-extensible metadata
);

-- ---------------------------------------------------------------------
-- sync_state — for the future sidecar's cursor (reserved, unused in OSS)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- End of schema v1.
```

### 6.3 Hook event type enum

Canonical Claude Code hook event names (known as of 2026-04):

- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `Notification`
- `PreCompact`
- `PostCompact`
- `Stop`
- `SubagentStop`
- `SessionEnd`

Plugins MAY write rows with `event_type` values outside this list, prefixed with their plugin name (e.g., `"agentaudit.hook_response"`, `"my-plugin.observation"`). The prefix convention avoids collisions.

### 6.4 Payload canonicalization

Before hashing, the payload JSON MUST be canonicalized:

- UTF-8 encoding.
- Sorted keys.
- No whitespace between tokens.
- Numbers in their canonical JSON form (no leading zeros, no trailing zeros on integers, `1.5e3` → `1500`, etc.).

Use Python's `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`. This gives a deterministic string.

### 6.5 Hash chain algorithm

Let `H(x)` = SHA-256(x) as hex string.

For the k-th row in a session:

- If k == 1: `prev_hash = NULL`.
- If k > 1: `prev_hash = row_hash of row (k-1) for this session_id`.

`row_hash` is computed over the canonical JSON of the row excluding the `row_hash` field itself but INCLUDING `prev_hash`:

```python
def compute_row_hash(row_without_hash: dict, prev_hash: str | None) -> str:
    # Fields in the hash input, in this exact order (via sorted keys):
    # session_id, sequence, event_type, plugin_name,
    # payload_json, timestamp, captured_at, prev_hash
    hash_input = {
        "captured_at":  row_without_hash["captured_at"],
        "event_type":   row_without_hash["event_type"],
        "payload_json": row_without_hash["payload_json"],
        "plugin_name":  row_without_hash["plugin_name"],
        "prev_hash":    prev_hash,  # NULL serializes as JSON null
        "sequence":     row_without_hash["sequence"],
        "session_id":   row_without_hash["session_id"],
        "timestamp":    row_without_hash["timestamp"],
    }
    canonical = json.dumps(hash_input, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

### 6.6 Write API (SDK)

```python
from nativeagents_sdk.audit import open_store, write_event, AuditEvent

conn = open_store()  # opens ~/.nativeagents/audit.db

event = AuditEvent(
    session_id="abc123",
    event_type="my-plugin.observation",
    plugin_name="my-plugin",
    payload={"tool_name": "Read", "file_path": "/etc/hosts"},
    timestamp=datetime.now(timezone.utc),
)

row_hash = write_event(conn, event)
```

`write_event` is responsible for:

1. Acquiring a transaction.
2. Looking up the last `row_hash` for `event.session_id` (ORDER BY sequence DESC LIMIT 1).
3. Computing `sequence = last_sequence + 1` (or 1 if none).
4. Canonicalizing `payload` to JSON.
5. Computing `row_hash`.
6. Inserting the row.
7. Committing.
8. Returning the new `row_hash`.

Concurrency: SQLite's WAL mode permits one writer at a time; concurrent writers will serialize on the transaction. The SDK does NOT implement its own cross-process lock — SQLite does that.

### 6.7 Verify API

```python
from nativeagents_sdk.audit import verify_integrity

report = verify_integrity(conn, session_id=None)  # all sessions
# report: { "sessions_verified": N, "breaks": [...] }
```

A "break" is a row whose recomputed `row_hash` does not match the stored one, OR whose `prev_hash` does not match the previous row's `row_hash`, OR a missing row (`sequence` gap).

### 6.8 Non-insertion operations

- `UPDATE events` — forbidden. The SDK does not expose an update API. Direct SQL updates are detectable via verify_integrity (they break the chain).
- `DELETE FROM events` — forbidden for plugins. Future retention/tombstone mechanism will be defined in a later schema version and is NOT part of v1.

---

## 7. Memory manifest: `manifest.json` + memory file frontmatter

### 7.1 Directory layout

```
~/.nativeagents/memory/
├── manifest.json                    # generated; kept in sync by agentmemory
├── <category>/                      # suggested: core, relationship, projects, procedures, working, reference
│   └── <filename>.md
```

### 7.2 `manifest.json` schema

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-19T14:30:00Z",
  "total_token_budget": 4096,
  "files": [
    {
      "path": "core/user.md",
      "name": "Who — core user identity",
      "description": "Top-level facts about the user",
      "category": "core",
      "token_budget": 400,
      "write_protected": false,
      "created_at": "2026-03-15T09:00:00Z",
      "updated_at": "2026-04-18T22:00:00Z",
      "tags": ["identity"],
      "extra": {}
    }
  ]
}
```

Rules:

- `path` MUST be relative to `~/.nativeagents/memory/`.
- `path` MUST be unique across the `files` array.
- `token_budget` is an integer ≥ 0; 0 means "no limit."
- `total_token_budget` is an integer ≥ 0; 0 means "no global limit."
- `category` is a string — the suggested set is listed above, but plugins MAY use any string for forward-compat.
- `write_protected` MUST be respected by any tool that edits memory files.
- `extra` is a free-form object for plugin-specific metadata; readers MUST preserve it on round-trip.

### 7.3 Memory file frontmatter

Each memory file is Markdown with YAML frontmatter:

```markdown
---
name: Who — core user identity
description: Top-level facts about the user
category: core
token_budget: 400
write_protected: false
created_at: 2026-03-15T09:00:00Z
updated_at: 2026-04-18T22:00:00Z
tags: [identity]
---

## Who

- Nagarjun, founder at Native Agents
- Building the cognitive stack for Claude Code
```

Frontmatter rules:

- Frontmatter MUST be at the top of the file, delimited by `---` on its own line.
- Keys MUST match `manifest.json` entry keys.
- `category` MUST match the directory the file lives in (lint-enforced, not load-enforced — readers tolerate mismatches).
- Any frontmatter key not in the spec is preserved on round-trip as `extra.<key>`.

### 7.4 Manifest rebuild

The manifest is rebuilt by scanning the memory directory:

```python
from nativeagents_sdk.memory import rebuild_manifest
from nativeagents_sdk.paths import memory_dir

manifest = rebuild_manifest(memory_dir())
# Scans all .md files, parses frontmatter, returns a Manifest.
```

Plugins MAY maintain the manifest incrementally (updating on PostToolUse when a memory file is modified) or fully (rebuild every time). The format is the same.

---

## 8. Hook script contract

### 8.1 Shape

Every plugin ships a hook script that Claude Code invokes. The script's only responsibility is to hand control to Python.

Canonical template (lives at `src/nativeagents_sdk/hooks/template.sh` in this repo; plugins render it at install time):

```bash
#!/usr/bin/env bash
# Native Agents plugin hook wrapper.
# Generated from nativeagents-sdk template — DO NOT EDIT.
#
# Contract:
#   - stdin: JSON hook event payload from Claude Code
#   - env:   HOOK_EVENT_NAME (preferred) — the event type
#   - exit:  0 (always, unless explicit block with exit 2)
#
# This wrapper NEVER blocks Claude Code. Python-level errors are logged.

set -u
# Deliberately NOT set -e: the Python handler manages its own error flow.

PLUGIN_NAME="{{PLUGIN_NAME}}"
PYTHON="{{PYTHON_EXECUTABLE}}"
MODULE="{{PYTHON_MODULE}}"

export PYTHONUNBUFFERED=1
export NATIVEAGENTS_PLUGIN_NAME="$PLUGIN_NAME"

# Forward stdin + env + args to the Python entry point.
# The Python side is responsible for reading stdin, dispatching,
# logging errors, and exiting with 0 (or 2 for explicit block).
"$PYTHON" -m "$MODULE" "$@"
rc=$?

# Policy: propagate exit code 2 (explicit block).
# Otherwise force 0 so Claude Code is never blocked by plugin bugs.
if [ "$rc" = "2" ]; then
    exit 2
fi
exit 0
```

### 8.2 stdin payload

Claude Code writes a JSON object to stdin. The exact shape depends on the event type; see the Pydantic models in `src/nativeagents_sdk/schema/events.py`. The SDK-defined base shape:

```json
{
  "hook_event_name": "PreToolUse",
  "session_id": "abc123",
  "cwd": "/Users/nag/code/project",
  "permission_mode": "allow",
  "transcript_path": "/Users/nag/.claude/projects/.../abc123.jsonl",
  "tool_name": "Read",
  "tool_input": { "file_path": "/etc/hosts" }
}
```

Event-specific fields:

- `PreToolUse`, `PostToolUse`: `tool_name`, `tool_input`. `PostToolUse` adds `tool_result`.
- `UserPromptSubmit`: `user_prompt`.
- `Stop`, `SubagentStop`: `reason`.
- `Notification`: `message`.
- `PreCompact`, `PostCompact`: (implementation-defined — consult `agentaudit-cc/src/agentaudit/schema.py`).

### 8.3 Env vars

- `HOOK_EVENT_NAME` — preferred source of event type (set by modern Claude Code versions).
- `CLAUDE_HOME` — optional override for `~/.claude`.
- `NATIVEAGENTS_HOME` — optional override for `~/.nativeagents`.
- `NATIVEAGENTS_PLUGIN_NAME` — set by the template to the plugin's name; read by the dispatcher.

### 8.4 Exit codes

- `0` — hook handled successfully OR hook errored (errors are logged, not propagated).
- `2` — explicit block. Claude Code will refuse to proceed. Only policy enforcement should emit this.
- Any other non-zero — treated as an error by Claude Code; undesirable.

The SDK's dispatcher MUST catch all exceptions, log them, and return exit 0 unless a handler explicitly returns a `HookDecision.block(...)`.

---

## 9. Hook dispatcher Python API

### 9.1 Core classes

```python
# nativeagents_sdk.hooks

class HookDispatcher:
    def __init__(self, plugin_name: str) -> None: ...
    def on(self, event_name: str) -> Callable[[F], F]:
        """Decorator to register a handler."""
    def run(self) -> None:
        """Read stdin, dispatch, log, exit."""
```

```python
# nativeagents_sdk.hooks

@dataclass
class HookContext:
    plugin_name: str
    plugin_dir: Path           # ~/.nativeagents/plugins/<name>/ or well-known
    audit_db: Path             # ~/.nativeagents/audit.db
    config: Config             # loaded config.yaml
    log: logging.Logger        # writes to <plugin_dir>/logs/hook.log

    def write_audit(self, event_type: str, payload: dict, *, session_id: str | None = None) -> str:
        """Convenience: writes an audit event, returns row_hash."""
```

```python
# nativeagents_sdk.hooks

class HookDecision:
    @classmethod
    def ok(cls) -> "HookDecision": ...
    @classmethod
    def block(cls, reason: str) -> "HookDecision": ...
```

### 9.2 Handler signature

```python
from nativeagents_sdk.hooks import HookDispatcher, HookContext, HookDecision
from nativeagents_sdk.hooks import PreToolUseInput, PostToolUseInput

dispatcher = HookDispatcher(plugin_name="my-plugin")

@dispatcher.on("PreToolUse")
def handle_pre(event: PreToolUseInput, ctx: HookContext) -> HookDecision:
    ctx.log.info(f"Tool: {event.tool_name}")
    ctx.write_audit("my-plugin.pre_tool", {"tool": event.tool_name}, session_id=event.session_id)
    return HookDecision.ok()

if __name__ == "__main__":
    dispatcher.run()
```

### 9.3 Dispatch semantics

- `dispatcher.run()` reads stdin, parses JSON, identifies event type (prefer `HOOK_EVENT_NAME` env, fall back to `hook_event_name` in payload).
- Finds the handler registered for that event type.
- If no handler is registered, exits 0 silently (this is a feature — plugins register only for events they care about).
- Instantiates the typed event model (e.g., `PreToolUseInput`) via Pydantic.
- Calls the handler with the event and a `HookContext`.
- Catches all exceptions, logs them to `<plugin_dir>/logs/hook.log`.
- If the handler returned `HookDecision.block(reason)`, prints `reason` to stderr and exits 2.
- Otherwise exits 0.

### 9.4 Thread safety

`HookDispatcher` is NOT thread-safe. Hooks are single-shot invocations per process (fork/exec pattern); the dispatcher is created once and `.run()` once per invocation.

### 9.5 Imports

`from nativeagents_sdk.hooks import ...` exposes:

- `HookDispatcher`, `HookContext`, `HookDecision`
- Event models: `HookInput`, `SessionStartInput`, `UserPromptSubmitInput`, `PreToolUseInput`, `PostToolUseInput`, `NotificationInput`, `PreCompactInput`, `PostCompactInput`, `StopInput`, `SubagentStopInput`, `SessionEndInput`

---

## 10. Spool format

### 10.1 Directory layout

```
~/.nativeagents/spool/<plugin_name>/<kind>/
├── .tmp/                            # incomplete writes land here; never read
│   └── <pid>-<random>.bin
├── 2026-04-19T14-30-00.123456-<random>.bin
├── 2026-04-19T14-30-01.245678-<random>.bin
└── ...
```

### 10.2 Filenames

- Completed files: `<iso-timestamp-with-colons-replaced-by-dashes>-<8-char-random>.bin`.
- Iterating with `sorted(os.listdir(...))` yields chronological order.
- Random suffix avoids collisions within a microsecond window.

### 10.3 Write algorithm

```python
# Pseudo-code for Spool.write(data)

tmp_dir = spool_dir / ".tmp"
tmp_dir.mkdir(parents=True, exist_ok=True)

tmp_name = f"{os.getpid()}-{secrets.token_hex(4)}.bin"
tmp_path = tmp_dir / tmp_name

with open(tmp_path, "wb") as f:
    f.write(data)
    f.flush()
    os.fsync(f.fileno())

final_name = f"{datetime.now(timezone.utc).isoformat().replace(':', '-')}-{secrets.token_hex(4)}.bin"
final_path = spool_dir / final_name

os.replace(tmp_path, final_path)

return final_path
```

### 10.4 Consume algorithm

```python
# Pseudo-code for draining

for path in sorted(spool_dir.iterdir()):
    if path.is_dir() or path.name.startswith("."):
        continue
    data = path.read_bytes()
    handle(data)
    path.unlink(missing_ok=True)
```

A consumer that crashes between `handle(data)` and `path.unlink()` will re-process the file on restart — consumers MUST be idempotent, or they MUST write a sidecar acknowledgment file before calling `handle`.

### 10.5 Content format

The spool is content-agnostic. Contents are opaque bytes. Conventions:

- For kind `audit`: UTF-8 JSON, one event per file.
- For kind `inbox`: MIME-typed with a `Content-Type` first line, or raw markdown for seed files.
- For kind `outbound` (future): Protocol Buffers or JSON, defined by the sidecar.

---

## 11. Install registration: `~/.claude/settings.json` merge rules

### 11.1 Claude Code settings shape

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "/path/to/hook.sh" } ] }
    ],
    "PreToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "/path/to/hook.sh" } ] }
    ]
  }
}
```

(Exact shape may evolve with Claude Code. Consult `agentaudit-cc/src/agentaudit/installation.py` for the current reference.)

### 11.2 SDK entries

Every hook entry the SDK adds carries an identifying field:

```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "/path/to/hook.sh",
      "nativeagents_plugin": "my-plugin"
    }
  ]
}
```

The `nativeagents_plugin` field lets `register_plugin` and `unregister_plugin` distinguish SDK-managed entries from user-added ones.

### 11.3 Register API

```python
from nativeagents_sdk.install import register_plugin
from nativeagents_sdk.plugin.manifest import load_plugin_manifest
from pathlib import Path

register_plugin(
    manifest=load_plugin_manifest(Path("plugin.toml")),
    hook_script=Path("/abs/path/to/hook.sh"),
)
```

Algorithm:

1. Read `~/.claude/settings.json` (if exists) or start with `{"hooks": {}}`.
2. Write backup: `~/.claude/settings.json.bak.<timestamp>`.
3. For each event in `manifest.plugin.hooks`:
   - Ensure `hooks[<event>]` is a list.
   - Check if any existing entry has `nativeagents_plugin == manifest.plugin.name`. If yes, skip (idempotent).
   - Otherwise, append a new entry with the correct shape (including `nativeagents_plugin` tag).
4. Atomic write back to `~/.claude/settings.json`.
5. Copy the plugin's `plugin.toml` into `~/.nativeagents/plugins/<name>/` (or well-known directory).
6. Create the plugin's state directory and `logs/` subdirectory.

### 11.4 Unregister API

```python
from nativeagents_sdk.install import unregister_plugin
unregister_plugin("my-plugin")
```

Algorithm:

1. Read settings.
2. Backup.
3. For each event in settings, filter out entries where `nativeagents_plugin == name`.
4. Prune empty event arrays.
5. Atomic write.
6. Does NOT delete `~/.nativeagents/plugins/<name>/` — that's the plugin's data. The plugin's own uninstall flow handles data cleanup.

### 11.5 Idempotency guarantee

- `register_plugin` N times with the same args MUST produce the same final `settings.json`.
- `unregister_plugin` of a non-registered plugin MUST be a no-op (no error).
- Interleaving register/unregister MUST converge to the correct state.

---

## 12. Config file: `config.yaml`

### 12.1 Location

`~/.nativeagents/config.yaml`. Optional — SDK tolerates absence and returns defaults.

### 12.2 Schema (v1)

```yaml
schema_version: 1

# Global toggles
logging:
  level: INFO                       # DEBUG | INFO | WARNING | ERROR
  directory: ~/.nativeagents/logs   # absolute path; defaults to this

# Audit settings
audit:
  enabled: true
  # If true, verify_integrity is run at startup of any long-lived plugin process.
  verify_on_startup: false

# Per-plugin config blocks (free-form; each plugin defines its own schema)
plugins:
  agentaudit:
    neo4j_uri: null
    neo4j_user: null
    # etc — agentaudit-cc defines this shape
  agentmemory:
    total_token_budget: 4096
  agentwiki:
    cron_schedule: "0 */6 * * *"

# Reserved for future sidecar use — ignored in OSS.
sidecar:
  enabled: false
```

### 12.3 Validation

- `schema_version` MUST be 1.
- `logging.level` MUST be one of the listed levels.
- `plugins.<name>` is free-form — the SDK does not validate (each plugin validates its own block).

### 12.4 Python API

```python
from nativeagents_sdk.config import load_config, save_config, Config

cfg: Config = load_config()
cfg.plugins.setdefault("my-plugin", {})["token_budget"] = 500
save_config(cfg)
```

---

## 13. CLI conventions

### 13.1 Plugin CLIs

Each plugin SHOULD expose a CLI named after itself: `agentaudit`, `agentmemory`, `agentwiki`, `<plugin-name>`. The CLI SHOULD support the following common subcommands:

- `<plugin> version` — prints SDK version, plugin version, schema versions.
- `<plugin> doctor` — runs the doctor report from the SDK; exits 0 if healthy.
- `<plugin> show` — displays current plugin state to stdout.
- `<plugin> init` — interactive setup / install (plugin-specific).

The `show`, `init`, and plugin-specific subcommands are left to the plugin. The `version` and `doctor` subcommands SHOULD use SDK helpers (`sdk.install.doctor`, `sdk.version`).

### 13.2 SDK CLI

The SDK itself exposes `nativeagents-sdk` with subcommands:

- `nativeagents-sdk init-plugin <name>` — scaffold a new plugin.
- `nativeagents-sdk validate-plugin [path]` — conformance harness.
- `nativeagents-sdk check-contract` — doctor over all installed plugins.
- `nativeagents-sdk version` — prints SDK version.

### 13.3 Output

CLIs SHOULD write human-readable output to stdout, errors to stderr, and support `--json` for machine-readable output where relevant.

---

## 14. Error handling and exit codes

### 14.1 Exception hierarchy

```python
# nativeagents_sdk.errors

class SDKError(Exception):
    """Base."""

class ConfigError(SDKError): ...
class PluginManifestError(SDKError): ...
class ManifestError(SDKError): ...           # memory manifest
class FrontmatterError(SDKError): ...
class AuditStoreError(SDKError): ...
class IntegrityError(SDKError): ...
class InstallError(SDKError): ...
class DuplicatePluginError(SDKError): ...
class ConformanceError(SDKError): ...
```

All SDK functions document which of these they may raise.

### 14.2 CLI exit codes

- `0` — success.
- `1` — generic failure.
- `2` — explicit block (hooks only; see §8.4).
- `3` — conformance violation (validate-plugin, check-contract).
- `4` — integrity violation (verify-integrity).
- `64`-`78` — reserved for future use, following sysexits.h conventions.

### 14.3 Logging

- All SDK modules log to `~/.nativeagents/logs/sdk.log` by default (file handler, rotating at 10MB, 5 backups).
- Level is `INFO` by default, overridable via `config.yaml` or `NATIVEAGENTS_LOG_LEVEL` env.
- Plugins log to `<plugin_dir>/logs/<plugin_name>.log`.

---

## 15. Versioning and schema evolution

### 15.1 SDK versioning

- SemVer.
- Pre-1.0: breaking changes permitted, documented in CHANGELOG.md.
- 1.0 and after: breaking changes require a major version bump.

### 15.2 On-disk schema versioning

Every on-disk file format carries `schema_version`:

- `audit.db` — `meta.schema_version` row.
- `config.yaml` — top-level `schema_version`.
- `manifest.json` — top-level `schema_version`.
- `plugin.toml` — top-level `schema_version`.

### 15.3 Migration rules

- Forward migration: the SDK MAY migrate older on-disk formats to newer ones automatically when it detects them at startup.
- Backward migration: not supported. If a user downgrades the SDK, they MUST re-initialize the affected files.
- Migration functions live in `src/nativeagents_sdk/audit/migrations.py` (and similar for other formats).

### 15.4 Forward compat (readers)

Readers MUST:

- Ignore unknown fields.
- Reject files with `schema_version > MAX_SUPPORTED` cleanly (raise, do not partially read).
- Accept files with `schema_version < CURRENT` if a migration path exists.

### 15.5 Reserved identifiers

- Field names starting with `_` are reserved for SDK internal use.
- Plugin names starting with `native-`, `sdk-`, `system-` are reserved.
- Event type prefixes `sdk.`, `system.`, `audit.` (without plugin prefix) are reserved.

---

## 16. Public Python API surface

This is the totality of what `from nativeagents_sdk import ...` exposes after v0.1.0. Anything else is internal and subject to change without notice.

```python
# Top-level convenience re-exports
from nativeagents_sdk import __version__

# Paths
from nativeagents_sdk.paths import (
    home, claude_home,
    plugin_dir, audit_db_path, memory_dir, wiki_dir, wiki_inbox_dir,
    policies_dir, spool_dir, bin_dir, config_path,
    ensure_dir, atomic_write,
    validate_plugin_name,
)

# Config
from nativeagents_sdk.config import (
    Config, LoggingConfig, AuditConfig,
    load_config, save_config, validate_config,
)

# Schema / models
from nativeagents_sdk.schema.events import (
    HookEventType,
    HookInput,
    SessionStartInput, UserPromptSubmitInput,
    PreToolUseInput, PostToolUseInput,
    PreCompactInput, PostCompactInput,
    NotificationInput,
    StopInput, SubagentStopInput, SessionEndInput,
    HOOK_INPUT_MODELS,
)
from nativeagents_sdk.schema.audit import AuditEvent
from nativeagents_sdk.schema.manifest import MemoryFile, Manifest
from nativeagents_sdk.schema.frontmatter import Frontmatter
from nativeagents_sdk.schema.plugin import PluginManifest, PluginRequires

# Audit store
from nativeagents_sdk.audit import (
    open_store, write_event, read_events,
    get_last_hash, verify_integrity,
    VerificationReport,
)

# Memory
from nativeagents_sdk.memory import (
    load_manifest, save_manifest, rebuild_manifest,
    parse_frontmatter, render_frontmatter,
)

# Hooks
from nativeagents_sdk.hooks import (
    HookDispatcher, HookContext, HookDecision,
)

# Spool
from nativeagents_sdk.spool import Spool

# Install
from nativeagents_sdk.install import (
    register_plugin, unregister_plugin, is_registered,
    doctor, DoctorReport,
)

# Plugin discovery
from nativeagents_sdk.plugin import (
    load_plugin_manifest, save_plugin_manifest,
    discover_plugins, resolve_plugin,
)

# Errors
from nativeagents_sdk.errors import (
    SDKError, ConfigError, PluginManifestError, ManifestError,
    FrontmatterError, AuditStoreError, IntegrityError,
    InstallError, DuplicatePluginError, ConformanceError,
)
```

Implementation note: at the top-level `src/nativeagents_sdk/__init__.py`, only re-export `__version__` by default. Callers import submodules explicitly. This keeps cold-import time fast.

---

## 17. Non-goals (explicitly OUT of scope for v0.1)

The following are NOT part of the SDK and MUST NOT be implemented here:

- Real-time or streaming push of audit events. Sidecar territory.
- Network I/O of any kind. The SDK is local-only.
- Encryption at rest (SQLCipher) — plugin-specific if needed.
- Neo4j projection or any graph database. Stays in agentaudit-cc.
- Memory autoload / context injection. Stays in agentmemory-cc.
- Wiki graph building or cron scheduling. Stays in agentwiki-cc.
- Policy evaluation engine (regex/glob/shell matchers). Stays in agentaudit-cc.
- LLM calls or agent orchestration. Out of scope.
- TypeScript / Node.js wrappers. Future VS Code extension is a separate repo.
- GUI. CLI-only.
- MDM packaging or signing workflow. Future paid-side work.
- Cloud-side receivers or protocol buffers. Sidecar territory.

---

## 18. Reference: minimal conformant plugin

As a concrete illustration of this spec, here's a minimal plugin in full.

### `plugin.toml`

```toml
schema_version = 1

[plugin]
name = "hello-plugin"
version = "0.1.0"
description = "A minimal example plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = ["plugins/hello-plugin/"]
cli_entry = "hello_plugin.cli:app"
hook_module = "hello_plugin.hook"
min_sdk_version = "0.1.0"
```

### `src/hello_plugin/hook.py`

```python
from nativeagents_sdk.hooks import HookDispatcher, HookDecision, PreToolUseInput

dispatcher = HookDispatcher(plugin_name="hello-plugin")

@dispatcher.on("PreToolUse")
def on_pre(event: PreToolUseInput, ctx) -> HookDecision:
    ctx.log.info(f"Observed tool: {event.tool_name}")
    ctx.write_audit(
        event_type="hello-plugin.observation",
        payload={"tool": event.tool_name, "input_keys": list(event.tool_input.keys())},
        session_id=event.session_id,
    )
    return HookDecision.ok()

if __name__ == "__main__":
    dispatcher.run()
```

### `src/hello_plugin/cli.py`

```python
import typer
from nativeagents_sdk.install import doctor
from nativeagents_sdk import __version__ as sdk_version
from . import __version__ as plugin_version

app = typer.Typer()

@app.command()
def version():
    typer.echo(f"hello-plugin {plugin_version} (sdk {sdk_version})")

@app.command("doctor")
def doctor_cmd():
    report = doctor("hello-plugin")
    typer.echo(report.to_text())
    raise typer.Exit(0 if report.is_healthy else 1)
```

### `install.py`

```python
from pathlib import Path
from nativeagents_sdk.install import register_plugin
from nativeagents_sdk.plugin import load_plugin_manifest

manifest = load_plugin_manifest(Path("plugin.toml"))
hook_script = Path(__file__).parent / "hooks" / "hook.sh"

register_plugin(manifest=manifest, hook_script=hook_script)
print("hello-plugin installed.")
```

### `hooks/hook.sh`

Generated from the SDK template at install time:

```bash
#!/usr/bin/env bash
set -u
PLUGIN_NAME="hello-plugin"
PYTHON="/Users/nag/.venvs/hello-plugin/bin/python3"
MODULE="hello_plugin.hook"
export PYTHONUNBUFFERED=1
export NATIVEAGENTS_PLUGIN_NAME="$PLUGIN_NAME"
"$PYTHON" -m "$MODULE" "$@"
rc=$?
if [ "$rc" = "2" ]; then exit 2; fi
exit 0
```

That's the full surface area. The SDK provides everything else.

---

## 19. Implementation notes for the developer writing this SDK

1. **Start by writing `contract/*.md` files before any Python code.** Each section of this spec becomes a standalone contract doc. Writing them forces you to think through the edge cases BEFORE they become expensive in code.

2. **Test the hash chain with property-based testing.** Use Hypothesis to generate arbitrary sequences of events and assert: (a) the chain verifies, (b) any single-byte tampering breaks verification at the correct row.

3. **Test install flow with tmpdir-based fake `~/.claude/`.** Use the `NATIVEAGENTS_HOME` and `CLAUDE_HOME` env vars to redirect into `tmp_path` in pytest. Never touch the real user directories in tests.

4. **Keep the SDK import time under 200ms.** No top-level imports of heavy libraries. Lazy-import `pydantic` models only when needed. The hook path runs per Claude Code tool call — every millisecond matters.

5. **Extract, don't reinvent.** When implementing `hooks/runtime.py`, port the existing `agentaudit-cc/hooks/agentaudit-hook.sh` three-tier capture logic idea (daemon → spool → subprocess) as options the dispatcher can opt into. But for v0.1, the simple "read stdin, dispatch, exit" path is enough.

6. **Cross-reference the three repos constantly.** When in doubt about a field name, schema shape, or flow, search all three existing repos to see how they handle it. Pick the most thoughtful version; flag in `CHANGELOG.md` when you diverge.

7. **Mark TODOs with explicit decision ownership.** `# TODO(spec): decide whether sessions.extra_json is plugin-owned or SDK-owned` — so it's clear who needs to resolve it.

8. **Run the conformance harness against `examples/minimal_plugin/` as you go.** The harness is both the acceptance test for the SDK and the canonical demonstration that the SDK works.

---

End of specification.
