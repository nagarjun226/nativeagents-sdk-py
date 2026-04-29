# nativeagents-sdk-py — Build Plan

> **Audience for this document:** a fresh Claude Code session that will implement the SDK. You have no prior conversation context. Read this file first, then `spec.md`, then `successcriteria.md`. Then start on Milestone 0.

---

## 0. Purpose of this repo

`nativeagents-sdk-py` is the **shared contract and shared primitives** that every Native Agents plugin depends on. It is the foundation layer of the Native Agents OSS plugin ecosystem.

Three things live in this repo:

1. **Written specification** (the contract) — the canonical source of truth for file formats, directory layouts, SQLite schemas, hook protocols, and plugin manifests.
2. **Reference Python implementation** (the SDK library) — importable helpers that implement the spec so plugin authors don't have to reimplement hash chains, frontmatter parsers, hook dispatchers, or install flows themselves.
3. **Conformance tooling** — a test harness that a plugin can run to verify it conforms to the SDK contract.

The goal is: **a third party can write a 100-line Python plugin against this SDK and have it work seamlessly alongside `agentaudit-cc`, `agentmemory-cc`, and `agentwiki-cc` on a developer's machine, and its data will flow up through the (future, paid) Native Agents sidecar without any additional work.**

---

## 1. Where this repo fits in the broader architecture

Native Agents is a three-layer product:

- **OSS plugin layer** (where this SDK lives): three first-party plugins (`agentaudit-cc`, `agentmemory-cc`, `agentwiki-cc`), this SDK, and eventually a super-repo (`nativeagents-cc`) that bundles the three into a single marketplace-ready distribution. All of this is MIT-licensed, installable standalone, and useful without any cloud connection.
- **Paid managed sidecar** (future, closed source): a signed binary deployed to developer machines via the enterprise customer's MDM (Jamf / Intune / Workspace ONE). The sidecar tails the audit log, watches memory manifests, watches the raw inbox, and ships data to the cloud gateway over mTLS.
- **Paid hosted cloud** (future, closed source): gateway, S3, Postgres, ClickHouse, Neo4j, Kafka+Flink, admin dashboard, SIEM fan-out.

This SDK sits at the bottom of the OSS layer. **It is OSS. It is installable from PyPI. It has zero cloud dependencies.** The paid side reads the same contract the SDK defines, but it is not implemented here.

For full architectural context, read `/sessions/magical-sharp-goodall/mnt/.auto-memory/native_agents_architecture.md`.

---

## 2. Required reading before you write a line of code

Read these files, in this order, before starting Milestone 0. They are the existing implementations you will extract the SDK out of. Do not skim — the SDK design decisions depend on what these already do and where they diverge.

### Architecture and product context

- `/sessions/magical-sharp-goodall/mnt/.auto-memory/native_agents_architecture.md` — the load-bearing architecture memory. Read in full.
- `/sessions/magical-sharp-goodall/mnt/.auto-memory/MEMORY.md` — index of memory files (short).

### agentaudit-cc (the biggest, most mature repo — this is the primary source)

- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/README.md` — overall design.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/CLAUDE.md` — design notes for Claude Code contributors.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/schema.py` — Pydantic models for hook events (316 lines). This is the **authoritative shape** of every Claude Code hook payload.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/storage.py` — SQLite DDL, `write_event`, hash chain, migrations (1,029 lines). The SQL schema here is the source of truth.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/integrity.py` — hash chain verification (284 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/events.py` — in-memory event model and serialization (206 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/config.py` — config loader (81 lines, small, worth extracting).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/installation.py` — hook registration in `~/.claude/settings.json` (308 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/collector.py` — spool-write (231 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/src/agentaudit/drain.py` — spool-drain (266 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/hooks/agentaudit-hook.sh` — the reference hook script. Read fully.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentaudit-cc/pyproject.toml` — dependency set and packaging choices.

### agentmemory-cc

- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/README.md`
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/SPEC.md` — existing spec, 319 lines. Read in full.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/src/agentmemory/manifest.py` — memory manifest format (237 lines). **This is the authoritative shape of `manifest.json`.**
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/src/agentmemory/config.py` — config loader (184 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/src/agentmemory/context.py` — hook injection of context at `SessionStart` (198 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/src/agentmemory/validation.py` — frontmatter validation (128 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/src/agentmemory/onboarding.py` — install/setup flow (395 lines).
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentmemory-cc/hooks/agentmemory-hook.sh`

### agentwiki-cc

- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentwiki-cc/README.md`
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentwiki-cc/SPEC.md` — existing spec, 1,767 lines. Read selectively — chapters on the frontmatter and spool patterns are relevant; chapters on graph-specific logic are not.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentwiki-cc/src/agentwiki/frontmatter.py` — YAML frontmatter parser (117 lines). Extract this verbatim.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentwiki-cc/src/agentwiki/spool.py` — spool primitive (93 lines). Extract this verbatim.
- `/sessions/magical-sharp-goodall/mnt/nativeagents/agentwiki-cc/src/agentwiki/init_cmd.py` — install flow (583 lines).

After reading: **spend time skimming divergences.** The three repos do similar things differently. Your job is to pick the best version of each and codify it in the SDK.

---

## 3. What this SDK is (and is not)

### What it IS

- A Python library (`nativeagents_sdk`) publishable to PyPI.
- A set of Markdown specification documents in `contract/` that are the canonical reference.
- A conformance test suite that any plugin can run against itself.
- A CLI (`nativeagents-sdk`) with utilities: `init-plugin`, `validate-plugin`, `check-contract`.

### What it is NOT

- **Not a plugin itself.** The SDK contains no hooks, no CLI commands, no functionality a developer would install directly. Only plugins install into `~/.nativeagents/`.
- **Not a framework.** A plugin that wants to implement the spec manually and not import our library is a first-class citizen. The contract is in Markdown; the library is a convenience.
- **Not cloud-aware.** Nothing in this repo reaches out to a network. Nothing knows about sidecars, gateways, or control planes. The cloud side will read the contract separately.
- **Not a monorepo.** This repo stands alone. The three plugins stay in their own repos and depend on this SDK via pip.
- **Not a runtime.** No long-running processes, no daemons, no cron jobs. Plugins own their own runtime.

---

## 4. Target repo layout

Create this structure during Milestone 0:

```
nativeagents-sdk-py/
├── README.md                           # short README, points at contract/ and examples/
├── LICENSE                             # MIT
├── pyproject.toml                      # hatchling build, Python 3.11+
├── plan.md                             # this file
├── spec.md                             # the technical specification (top-level, read second)
├── successcriteria.md                  # acceptance criteria
├── CHANGELOG.md                        # semver changelog
├── CONTRIBUTING.md                     # (stub for now)
│
├── contract/                           # the canonical written specification
│   ├── README.md                       # index of contract docs
│   ├── 01-directory-layout.md          # ~/.nativeagents/ tree
│   ├── 02-plugin-manifest.md           # plugin.toml format
│   ├── 03-audit-schema.md              # SQLite DDL, hash chain
│   ├── 04-memory-manifest.md           # manifest.json + frontmatter
│   ├── 05-hooks.md                     # hook script contract
│   ├── 06-spool.md                     # atomic-rename spool format
│   ├── 07-install-registration.md      # how plugins register with ~/.claude/settings.json
│   ├── 08-config.md                    # config.yaml format
│   ├── 09-cli-conventions.md           # naming, subcommand layout
│   └── 10-versioning.md                # schema evolution rules
│
├── src/
│   └── nativeagents_sdk/
│       ├── __init__.py                 # public API exports
│       ├── py.typed                    # PEP 561 marker
│       ├── version.py                  # __version__
│       │
│       ├── paths.py                    # ~/.nativeagents/ resolution, per-plugin paths
│       ├── config.py                   # config.yaml load/save/validate
│       │
│       ├── schema/
│       │   ├── __init__.py
│       │   ├── events.py               # Pydantic models for hook events
│       │   ├── audit.py                # SQLite DDL + event row model
│       │   ├── manifest.py             # memory manifest models
│       │   ├── frontmatter.py          # frontmatter schema
│       │   └── plugin.py               # plugin.toml models
│       │
│       ├── audit/
│       │   ├── __init__.py
│       │   ├── ddl.sql                 # the canonical SQLite schema, loaded at runtime
│       │   ├── store.py                # open_store, write_event, hash chain
│       │   ├── integrity.py            # verify_integrity
│       │   └── migrations.py           # schema migration helpers
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── manifest.py             # load/save/validate manifest.json
│       │   └── frontmatter.py          # parser + validator
│       │
│       ├── hooks/
│       │   ├── __init__.py
│       │   ├── dispatcher.py           # HookDispatcher: register handlers, dispatch from stdin
│       │   ├── template.sh             # templated bash wrapper
│       │   └── runtime.py              # exit-code rules, env vars, stdin parse
│       │
│       ├── spool/
│       │   ├── __init__.py
│       │   └── spool.py                # atomic-rename write, directory iteration
│       │
│       ├── install/
│       │   ├── __init__.py
│       │   ├── register.py             # edit ~/.claude/settings.json idempotently
│       │   ├── venv.py                 # manage ~/.nativeagents/bin/ venv (optional helper)
│       │   └── doctor.py               # self-check helpers for plugins
│       │
│       ├── plugin/
│       │   ├── __init__.py
│       │   ├── manifest.py             # load plugin.toml
│       │   └── discovery.py            # find installed plugins, enumerate namespaces
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py                 # entry point: nativeagents-sdk
│       │   ├── init_plugin.py          # scaffolds a new SDK-conformant plugin
│       │   ├── validate_plugin.py      # runs conformance checks
│       │   └── check_contract.py       # verifies ~/.nativeagents/ is in a valid state
│       │
│       └── conformance/
│           ├── __init__.py
│           ├── harness.py              # test harness a plugin can run
│           └── fixtures.py             # shared test fixtures
│
├── tests/
│   ├── conftest.py
│   ├── test_paths.py
│   ├── test_config.py
│   ├── test_schema_events.py
│   ├── test_audit_store.py
│   ├── test_audit_integrity.py
│   ├── test_audit_migrations.py
│   ├── test_memory_manifest.py
│   ├── test_memory_frontmatter.py
│   ├── test_hooks_dispatcher.py
│   ├── test_hooks_runtime.py
│   ├── test_spool.py
│   ├── test_install_register.py
│   ├── test_plugin_manifest.py
│   ├── test_plugin_discovery.py
│   ├── test_cli_init_plugin.py
│   ├── test_cli_validate_plugin.py
│   ├── test_conformance_harness.py
│   └── fixtures/
│       ├── minimal_plugin.toml
│       ├── minimal_manifest.json
│       ├── sample_claude_settings.json
│       └── sample_hook_events/
│           ├── session_start.json
│           ├── pre_tool_use.json
│           ├── post_tool_use.json
│           ├── stop.json
│           └── ...
│
└── examples/
    ├── minimal_plugin/                 # a ~100-line reference plugin
    │   ├── README.md
    │   ├── plugin.toml
    │   ├── pyproject.toml
    │   ├── src/minimal_plugin/
    │   │   ├── __init__.py
    │   │   ├── hook.py                 # uses HookDispatcher
    │   │   └── cli.py                  # minimal CLI
    │   ├── hooks/hook.sh
    │   └── tests/test_minimal.py
    └── third_party_demo/               # simulates a 3rd-party plugin co-existing with the in-house three
        └── README.md                   # explains the co-existence invariants
```

---

## 5. Design principles (non-negotiable)

Follow these throughout. When in doubt, re-read.

1. **The contract is the product.** The Markdown spec in `contract/` is the source of truth. The Python library is a convenience that implements the spec. If the library and the spec disagree, fix the library — the spec wins. A plugin author must be able to conform to the spec without ever importing our library.

2. **No surprise I/O.** SDK functions never write to disk unless the caller explicitly asks. No implicit "initialize ~/.nativeagents on import" behavior. Paths are resolved deterministically from `NATIVEAGENTS_HOME` env var (default `~/.nativeagents`) and `CLAUDE_HOME` (default `~/.claude`).

3. **Idempotency everywhere.** Every install / register / unregister operation must be safe to run N times. If a plugin is already registered in `~/.claude/settings.json`, re-running `register_plugin()` is a no-op, not an error.

4. **Forward-compatible file formats.** Readers must not crash on unknown fields. Writers must always include the spec `schema_version` field. Migration logic lives in `audit/migrations.py` for the SQLite side and `schema/manifest.py` for JSON files.

5. **Plugins are isolated.** A plugin's bugs must not corrupt another plugin's state. This means: per-plugin namespaced subdirectories, per-plugin spool directories, no shared mutable Python state across plugins, and strict ownership rules in `plugin.toml` (a plugin declares what paths it writes).

6. **Hooks never block Claude Code.** The hook script always exits 0. Errors are logged, not propagated. This rule is already established in the three existing repos — the SDK must preserve it.

7. **Audit writes are append-only.** The `events` table in `audit.db` is append-only. No UPDATE, no DELETE. Hash chain enforces tamper evidence. The SDK's `write_event` API must make this easy to get right.

8. **No dependencies beyond the standard library + a small pinned set.** Allowed runtime deps: `pydantic>=2`, `pyyaml>=6`, `typer>=0.9`, `rich>=13`, `python-dateutil>=2.8`, `tomli>=2` (for Python <3.11 if we ever target it), and `tomli-w` for writing TOML. **No other deps without justification.** The SDK must be lightweight.

9. **Python 3.11+ only.** Reason: match the strictest of the three existing plugins (agentwiki-cc requires 3.11). Gives us `tomllib` in stdlib, `StrEnum`, better error messages.

10. **Cross-platform.** macOS and Linux on day one. Windows on day zero means avoiding POSIX-only primitives — use `os.replace()` for atomic renames (works on Windows), avoid `fcntl`, document any `os.fork()` use as Unix-only. Actual Windows CI job is a Milestone 7 goal.

11. **The SDK never imports a plugin.** Discovery is by filesystem convention (`~/.nativeagents/plugins/*/plugin.toml`). The SDK reads these manifests but does not `import` the plugin's Python package. This keeps the SDK from depending on any plugin being installed.

12. **Breaking changes are explicit.** The SDK version follows semver. Breaking changes to the on-disk format require a major version bump AND a migration script. Pre-1.0 (which we will stay in for months), we can make breaking changes more freely but must document them in `CHANGELOG.md`.

---

## 6. Build milestones

Each milestone is sized to be completed and tested before moving on. Do not skip ahead. The order is dependency-driven: each milestone builds on the previous.

### M0 — Scaffolding and tooling (day 1)

**Goal:** empty repo with working CI, tests that run, linting passes.

Steps:

1. Create the directory layout from §4 above (empty files where content is TBD).
2. Write `pyproject.toml` with:
   - `name = "nativeagents-sdk"`
   - `version = "0.0.1"` (read from `src/nativeagents_sdk/version.py`)
   - `requires-python = ">=3.11"`
   - Dependencies as listed in §5 principle 8.
   - Dev dependencies: `pytest>=7`, `pytest-cov>=4`, `ruff>=0.4`, `mypy>=1.8`, `hypothesis>=6` (for property tests on hash chain).
   - Hatch build, entry points for `nativeagents-sdk` CLI.
3. `src/nativeagents_sdk/__init__.py` exposes `__version__` only for now.
4. Write a minimal `tests/test_smoke.py` that imports the package and asserts version exists.
5. Write `.github/workflows/ci.yml` running pytest + ruff + mypy on Python 3.11 and 3.12, Ubuntu and macOS.
6. Write `LICENSE` (MIT, copyright Native Agents).
7. Commit. Run CI. It must be green before moving to M1.

Deliverable: green CI, empty but installable package.

---

### M1 — Path resolution and config (day 2)

**Goal:** the `paths` and `config` modules are implemented and tested.

Why first: every other module depends on "where is `~/.nativeagents/`" and "what does the user's config say."

Steps:

1. Write `contract/01-directory-layout.md` (start from the spec — see `spec.md` §3).
2. Write `contract/08-config.md` (see `spec.md` §9).
3. Implement `src/nativeagents_sdk/paths.py`:
   - `home() -> Path` — resolves `NATIVEAGENTS_HOME` env var, defaults to `~/.nativeagents`. Never creates the directory.
   - `claude_home() -> Path` — resolves `CLAUDE_HOME`, defaults to `~/.claude`.
   - `plugin_dir(plugin_name: str) -> Path` — returns `<home>/plugins/<plugin_name>`.
   - `audit_db_path() -> Path` — returns `<home>/audit.db`.
   - `memory_dir() -> Path` — returns `<home>/memory`.
   - `wiki_dir() -> Path` — returns `<home>/wiki`.
   - `wiki_inbox_dir() -> Path` — returns `<home>/wiki/raw-inbox`.
   - `policies_dir() -> Path` — returns `<home>/policies`.
   - `spool_dir() -> Path` — returns `<home>/spool`.
   - `bin_dir() -> Path` — returns `<home>/bin`.
   - `config_path() -> Path` — returns `<home>/config.yaml`.
   - Validate plugin names: lowercase, alphanumeric + hyphen, max 40 chars. Reject `.`, `..`, `/`, reserved names (`audit`, `memory`, `wiki`, `policies`, `spool`, `bin`, `plugins` — these are reserved subdirs).
   - `ensure_dir(path: Path)` — helper to mkdir -p (callers use this explicitly).
4. Implement `src/nativeagents_sdk/config.py`:
   - `Config` pydantic model matching the schema in `spec.md` §9.
   - `load_config(path: Path | None = None) -> Config` — if path is None, uses `paths.config_path()`. If file doesn't exist, returns `Config()` (defaults). Never writes.
   - `save_config(config: Config, path: Path | None = None) -> None` — writes YAML. Idempotent (same config → same bytes).
   - `validate_config(raw: dict) -> Config` — raises `ConfigError` with a helpful message.
5. Write `tests/test_paths.py`:
   - Plugin name validation (positive + negative cases).
   - Env var override respected.
   - All path helpers return expected shapes.
   - No paths are created as side effects of importing the module.
6. Write `tests/test_config.py`:
   - Load missing file → defaults.
   - Save + load round-trips.
   - Invalid config raises `ConfigError` with useful message.
   - Unknown fields are ignored (forward compat).
7. Update the minimal plugin example under `examples/minimal_plugin/` to import `nativeagents_sdk.paths` and print its namespace.

Deliverable: path and config helpers exported via `from nativeagents_sdk import paths, config`. All tests pass.

---

### M2 — Audit schema and SQLite store (days 3–5)

**Goal:** the audit write path (the most security-critical part of the SDK) is implemented and fuzzed.

Steps:

1. Write `contract/03-audit-schema.md` — extract from `agentaudit-cc/src/agentaudit/storage.py` and `schema.py`. Document:
   - `events` table DDL (canonical).
   - Column semantics.
   - Hash chain algorithm (SHA-256 of `prev_hash + session_id + sequence + event_type + payload_json`).
   - Insertion invariants (monotonic sequence per session, non-null hash, etc.).
   - PRAGMA settings (WAL mode, foreign_keys ON, etc.).
2. Create `src/nativeagents_sdk/audit/ddl.sql` — paste the DDL from step 1. Comment every column.
3. Implement `src/nativeagents_sdk/schema/audit.py`:
   - `AuditEvent` Pydantic model with fields: `session_id`, `sequence`, `event_type`, `plugin_name`, `payload` (JSON dict), `timestamp`, `captured_at`.
   - Validators for session_id (reuse from agentaudit's `schema.py` `validate_session_id`).
4. Implement `src/nativeagents_sdk/audit/store.py`:
   - `open_store(path: Path) -> sqlite3.Connection` — opens connection, enables WAL, applies PRAGMAs, creates schema if missing.
   - `write_event(conn, event: AuditEvent) -> str` — computes hash from `prev_hash + canonical_json(event)`, inserts row, returns new hash. Uses a transaction. Must be called with plugin-scoped write lock (see below).
   - `get_last_hash(conn, session_id: str) -> str | None` — fetches prev_hash for new sequence.
   - `read_events(conn, session_id: str, since_sequence: int = 0) -> Iterator[AuditEvent]` — read-only iterator.
   - `write_lock(conn)` — a context manager that serializes writes within a process. Multi-process locking is via SQLite's own locking in WAL mode — callers don't need to coordinate.
5. Implement `src/nativeagents_sdk/audit/integrity.py`:
   - `verify_integrity(conn, session_id: str | None = None) -> VerificationReport` — rehash each row in sequence order; return report with any breaks. Reuse the implementation shape in `agentaudit-cc/src/agentaudit/integrity.py`.
6. Implement `src/nativeagents_sdk/audit/migrations.py`:
   - `CURRENT_SCHEMA_VERSION = 1` constant.
   - `migrate(conn, target_version: int) -> None` — walks a list of migration callables. Each migration is a pure SQL + Python function that transforms schema version N to N+1.
   - For M2, we only have version 1 — so migrations list is empty, but the structure is in place.
7. Write `tests/test_audit_store.py`:
   - Round-trip a single event.
   - Round-trip 1,000 events, verify monotonic sequence.
   - Concurrent-writer test: two threads hammering write_event, all rows land, hash chain intact.
   - Forward-compat test: write with current schema, read with a mock "future" schema that has extra columns — should not crash.
8. Write `tests/test_audit_integrity.py`:
   - Clean chain verifies.
   - Tamper one row's payload → verify reports the break at exact row.
   - Tamper one row's hash → same.
   - Empty DB verifies trivially.
9. Write `tests/test_audit_migrations.py`:
   - Opening a DB with missing schema creates it.
   - Opening a DB with correct schema is a no-op.
   - (Future migration scaffolding can be asserted with a mock migration.)

Deliverable: `from nativeagents_sdk.audit import open_store, write_event, verify_integrity` all work. Hash chain is bulletproof under concurrent writes. 100% line coverage on the audit module.

**Note on reuse:** the existing `agentaudit-cc/src/agentaudit/storage.py` is 1,029 lines and does a LOT — including per-plugin projections, blobs, attestation, encryption. **The SDK extracts only the raw event-write path.** Projections, blobs, policy evaluation, encryption, and the transcript tailer stay in agentaudit-cc. The SDK's audit module is approximately 200–300 lines.

---

### M3 — Memory manifest and frontmatter (days 6–7)

**Goal:** memory manifest + frontmatter parsing extracted and unified.

Steps:

1. Write `contract/04-memory-manifest.md` — extract from `agentmemory-cc/SPEC.md` and `src/agentmemory/manifest.py`. Document:
   - `manifest.json` JSON schema (use JSON Schema draft-2020-12 for machine validation).
   - File frontmatter keys: `name`, `description`, `category`, `token_budget`, `write_protected`, `created_at`, `updated_at`, `tags`.
   - Canonical categories: `core`, `relationship`, `projects`, `procedures`, `working`, `reference` — but note in spec that plugins can add new categories; unknown categories are permitted (forward-compat).
2. Implement `src/nativeagents_sdk/schema/manifest.py`:
   - `MemoryFile` Pydantic model (one manifest entry).
   - `Manifest` Pydantic model (top-level, has `schema_version`, `files: list[MemoryFile]`, `generated_at`).
3. Implement `src/nativeagents_sdk/schema/frontmatter.py`:
   - `Frontmatter` Pydantic model.
   - Parser reused from `agentwiki-cc/src/agentwiki/frontmatter.py` (117 lines — extract verbatim, adapt for the unified Frontmatter model).
4. Implement `src/nativeagents_sdk/memory/manifest.py`:
   - `load_manifest(path: Path) -> Manifest` — validates, raises `ManifestError`.
   - `save_manifest(path: Path, m: Manifest) -> None` — writes JSON, atomic (via os.replace).
   - `rebuild_manifest(memory_dir: Path) -> Manifest` — scans all `.md` files, parses frontmatter, returns a fresh manifest. Used by agentmemory's `PostToolUse` hook to keep the manifest in sync.
   - `validate_file(path: Path) -> list[ValidationError]` — lints a single memory file.
5. Implement `src/nativeagents_sdk/memory/frontmatter.py`:
   - `parse(text: str) -> tuple[Frontmatter, str]` — returns (frontmatter, body).
   - `render(fm: Frontmatter, body: str) -> str` — serializes back.
6. Tests:
   - `tests/test_memory_manifest.py` — round-trip, rebuild, validation errors, forward-compat.
   - `tests/test_memory_frontmatter.py` — parse, render, malformed input handling.

Deliverable: `from nativeagents_sdk.memory import load_manifest, save_manifest, parse_frontmatter` work. Existing agentmemory test suite (ported) passes against the SDK implementation.

---

### M4 — Plugin manifest (day 8)

**Goal:** plugins can declare themselves.

Steps:

1. Write `contract/02-plugin-manifest.md`. This is a NEW concept — does not exist in the three plugins yet. See `spec.md` §5 for the spec.
2. Implement `src/nativeagents_sdk/schema/plugin.py`:
   - `PluginManifest` Pydantic model with fields defined in the spec.
3. Implement `src/nativeagents_sdk/plugin/manifest.py`:
   - `load_plugin_manifest(path: Path) -> PluginManifest` — reads `plugin.toml`, validates.
   - `save_plugin_manifest(path: Path, m: PluginManifest) -> None` — writes TOML.
4. Implement `src/nativeagents_sdk/plugin/discovery.py`:
   - `discover_plugins() -> list[PluginManifest]` — scans `<home>/plugins/*/plugin.toml` AND any plugin that's been registered globally (see next milestone). Returns all plugins found. Never raises — malformed plugin.toml files are logged and skipped.
   - `resolve_plugin(name: str) -> PluginManifest | None` — single-plugin lookup by name.
5. Tests:
   - `tests/test_plugin_manifest.py` — round-trip, schema validation, missing fields.
   - `tests/test_plugin_discovery.py` — sets up a tmp home with 2 plugins + 1 malformed, asserts discovery returns the 2 valid ones.

Deliverable: a plugin's `plugin.toml` is a first-class artifact.

---

### M5 — Hook dispatcher and template (days 9–10)

**Goal:** the hook script is a thin wrapper; all logic is Python.

Steps:

1. Write `contract/05-hooks.md`. See `spec.md` §6.
2. Implement `src/nativeagents_sdk/hooks/runtime.py`:
   - `read_hook_input() -> HookInput` — reads stdin, parses JSON, honors `HOOK_EVENT_NAME` env var, returns a typed event model (using models in `src/nativeagents_sdk/schema/events.py`).
   - Event models ported from `agentaudit-cc/src/agentaudit/schema.py` `HookInput` hierarchy.
   - `ok()` / `fail(msg: str)` / `block(reason: str)` — standard exit-code helpers matching Claude Code's hook protocol (`ok()` exits 0; `fail()` logs and exits 0 because hooks must never block; `block()` exits 2 to signal a deny decision — used only by policy enforcement).
3. Implement `src/nativeagents_sdk/hooks/dispatcher.py`:
   - `HookDispatcher(plugin_name: str)` class.
   - `@dispatcher.on("PreToolUse")` decorator to register a handler function.
   - `dispatcher.run()` — reads input, dispatches to matching handler, catches and logs exceptions, exits 0.
   - Handler signature: `def handler(event: PreToolUseInput, ctx: HookContext) -> None | HookDecision`.
   - `HookContext` exposes: `plugin_name`, `plugin_dir` (Path), `audit_db` (Path), `config` (Config), `log` (logger writing to `<plugin_dir>/hook.log`).
4. Implement `src/nativeagents_sdk/hooks/template.sh`:
   - A generic templated bash wrapper. Plugins render this to their own `hooks/hook.sh` at install time.
   - The template needs a `{{PYTHON_EXECUTABLE}}` and `{{PYTHON_MODULE}}` substitution.
   - Logic: set `PYTHONUNBUFFERED=1`, execute `"$PYTHON" -m "$MODULE"`, always exit 0 regardless of Python exit code (unless Python exits 2 for block — then propagate).
   - Use `set -u` but NOT `set -e` (handlers manage errors themselves).
5. Implement `src/nativeagents_sdk/hooks/__init__.py`:
   - Exports: `HookDispatcher`, `HookContext`, `HookDecision`, and all `*Input` event models.
6. Tests:
   - `tests/test_hooks_runtime.py` — stdin parsing, env var precedence, malformed JSON handling.
   - `tests/test_hooks_dispatcher.py` — decorator registration, dispatch, exception safety, block/ok/fail semantics.

Deliverable: a plugin can write a 10-line hook handler and register it in 3 lines.

---

### M6 — Spool primitive (day 11)

**Goal:** atomic-rename spool for deferred writes.

Steps:

1. Write `contract/06-spool.md`. See `spec.md` §7.
2. Implement `src/nativeagents_sdk/spool/spool.py`:
   - `Spool(plugin_name: str, kind: str)` — constructor. `kind` is typically `"audit"`, `"inbox"`, etc. Resolves to `<home>/spool/<plugin_name>/<kind>/`.
   - `Spool.write(data: bytes) -> Path` — writes to a temp file in `<dir>/.tmp/`, then `os.replace` into the spool dir with name `<timestamp>-<random>.bin`. Returns final path.
   - `Spool.iter() -> Iterator[Path]` — yields files in the spool dir sorted by filename (which is timestamp-prefixed).
   - `Spool.consume(path: Path) -> None` — deletes a spool file after successful drain. Atomic via `path.unlink(missing_ok=True)`.
3. Tests:
   - `tests/test_spool.py`:
     - Concurrent writers don't clobber each other.
     - `iter()` returns writes in timestamp order.
     - `consume()` is idempotent (double-consume doesn't raise).
     - Corrupted temp file left by a crash is not returned by `iter()` (because it was never renamed).

Deliverable: a plugin can use the spool in 5 lines.

---

### M7 — Install registration (days 12–13)

**Goal:** plugins can register their hooks with Claude Code idempotently.

Steps:

1. Write `contract/07-install-registration.md`. See `spec.md` §8.
2. Implement `src/nativeagents_sdk/install/register.py`:
   - `read_claude_settings() -> dict` — reads `~/.claude/settings.json`, returns dict (or empty dict if missing).
   - `register_plugin(manifest: PluginManifest, hook_script: Path) -> None`:
     - Merges hook entries into `settings.json`.
     - Uses a `nativeagents_plugin` key per-entry so we can identify our own entries and avoid duplicating them.
     - Atomic write: write to temp + `os.replace`.
     - Creates a backup copy at `~/.claude/settings.json.bak.<timestamp>` before modifying.
   - `unregister_plugin(plugin_name: str) -> None` — removes our entries for that plugin, leaves user's other entries untouched.
   - `is_registered(plugin_name: str) -> bool`.
3. Implement `src/nativeagents_sdk/install/venv.py` (optional helper):
   - `ensure_bin_dir()` — creates `<home>/bin/` if missing.
   - `create_venv(target: Path, python: str = "python3") -> Path` — creates a venv at `target`, returns path to the venv's Python.
   - Plugins that want to ship a stable venv use this; plugins that don't want it (and use system Python) skip it.
4. Implement `src/nativeagents_sdk/install/doctor.py`:
   - `doctor(plugin_name: str) -> DoctorReport` — runs a series of checks: plugin.toml valid, hook script exists and is executable, hook registered in Claude settings, `<home>/plugins/<name>/` exists and is writable.
5. Tests:
   - `tests/test_install_register.py`:
     - Register into empty settings.json — creates it with one entry.
     - Register into existing settings.json — preserves user entries.
     - Double-register — no-op.
     - Unregister — removes only our entries.
     - Backup file created.

Deliverable: `register_plugin()` is the one-stop install call.

---

### M8 — CLI (day 14)

**Goal:** `nativeagents-sdk init-plugin`, `validate-plugin`, `check-contract` work.

Steps:

1. Write `contract/09-cli-conventions.md` — not prescriptive, but recommends: every SDK-conformant plugin should expose a CLI named after itself (`agentaudit`, `agentmemory`, `agentwiki`, `<plugin-name>`) with subcommands `doctor`, `version`, `show`. The SDK's own CLI is `nativeagents-sdk`.
2. Implement `src/nativeagents_sdk/cli/main.py` — typer app.
3. Implement `src/nativeagents_sdk/cli/init_plugin.py`:
   - `nativeagents-sdk init-plugin <name>` scaffolds a new plugin directory.
   - Creates: `plugin.toml`, `pyproject.toml`, `src/<name>/hook.py` (with a minimal HookDispatcher example), `src/<name>/cli.py`, `tests/test_smoke.py`, `hooks/hook.sh.template`.
4. Implement `src/nativeagents_sdk/cli/validate_plugin.py`:
   - `nativeagents-sdk validate-plugin [path]` runs the conformance harness against a plugin directory.
5. Implement `src/nativeagents_sdk/cli/check_contract.py`:
   - `nativeagents-sdk check-contract` runs the doctor on all discovered plugins.
6. Tests:
   - `tests/test_cli_init_plugin.py` — runs init-plugin in tmpdir, asserts scaffold matches expectations.
   - `tests/test_cli_validate_plugin.py` — runs validate-plugin against the scaffolded plugin, asserts green.

Deliverable: someone can go from `pip install nativeagents-sdk` to a working plugin scaffold in 10 seconds.

---

### M9 — Conformance harness (day 15)

**Goal:** a plugin can run a battery of tests to prove it conforms.

Steps:

1. Implement `src/nativeagents_sdk/conformance/harness.py`:
   - `run_conformance(plugin_dir: Path) -> ConformanceReport`
   - Tests the plugin against a stream of synthetic hook events.
   - Asserts: plugin writes audit events correctly, plugin respects path namespacing, plugin's hook script exits 0, plugin.toml is valid.
2. Implement `src/nativeagents_sdk/conformance/fixtures.py`:
   - Shared hook-event fixtures (one per event type, realistic payloads).
3. Tests:
   - `tests/test_conformance_harness.py` — runs harness against `examples/minimal_plugin/`, asserts it passes.

Deliverable: `nativeagents-sdk validate-plugin` produces a green report for `examples/minimal_plugin/`.

---

### M10 — Example plugin and release (day 16)

**Goal:** ship v0.1.0.

Steps:

1. Flesh out `examples/minimal_plugin/`:
   - Plugin that logs every `PreToolUse` to its own local file AND writes an audit event.
   - ~100 lines of Python total.
   - Passes the conformance harness.
2. Write `README.md` for the SDK repo:
   - What is this.
   - Link to `contract/`.
   - Link to `examples/minimal_plugin/`.
   - Installation instructions.
   - Contribution notes.
3. Bump version to `0.1.0`. Update `CHANGELOG.md`.
4. Tag release. Publish to PyPI (or TestPyPI first, then PyPI).

Deliverable: `pip install nativeagents-sdk` works for third parties.

---

## 7. After M10 — downstream work (not in this repo)

These are NOT part of this repo's scope, but are listed here so you understand the context.

- **Refactor agentaudit-cc** to depend on `nativeagents-sdk`. Replace its schema.py, storage.py (audit slice), config.py, installation.py, frontmatter logic with SDK imports. This is ~2 weeks of work on agentaudit-cc, not here.
- **Refactor agentmemory-cc** similarly. ~1 week.
- **Refactor agentwiki-cc** similarly. ~1 week.
- **Create the super-repo** `nativeagents-cc` that bundles the three. ~1 week.
- **Marketplace submission** to the Claude plugin marketplace.
- (Much later) VS Code extension wrapper for the future Copilot audience.

---

## 8. Versioning strategy

- `nativeagents-sdk` follows SemVer.
- Pre-1.0 (which we will stay in for 3–6 months): breaking changes permitted but must be documented in CHANGELOG.md with migration notes.
- The SQLite schema version is tracked in a `schema_version` row in a `meta` table. Bumping the schema version requires a migration.
- The `plugin.toml` format has its own `schema_version` field.
- The `manifest.json` has its own `schema_version` field.
- The `config.yaml` has its own `schema_version` field.

Rule of thumb: **every on-disk format carries a `schema_version` field and has a migration path.** A 3rd-party plugin depending on `nativeagents-sdk>=0.1,<0.2` should continue to work after an SDK 0.1.x patch without code changes.

---

## 9. Testing strategy

- **Unit tests** for every module. Target ≥90% line coverage.
- **Property-based tests** (via Hypothesis) for the hash chain: any sequence of valid events produces a verifiable chain; any single-byte tampering is detected.
- **Integration tests** that exercise the full flow: scaffolded plugin → register → fire hook events → check audit.db → validate integrity.
- **Multi-process tests** for spool and audit writes (use `multiprocessing.Process`).
- **Cross-platform CI** for macOS + Linux on Python 3.11 + 3.12 from day one. Windows CI is a Milestone 7+ nice-to-have.
- **Linting** via `ruff`, strict mode.
- **Type checking** via `mypy --strict` on `src/nativeagents_sdk/`. Tests can be less strict.
- **No flakiness policy**: any test that is flaky in CI gets fixed or deleted — never retried.

---

## 10. Open questions / decisions deferred

These are questions to flag in `contract/README.md` under "Open Questions" and leave as TODOs until you (or a human) decide:

1. **Should the audit DB be one shared `audit.db` or one per plugin?**
   - Pro shared: cross-plugin correlation in a single query. Sidecar tails one file.
   - Pro per-plugin: isolation, no write contention.
   - Current recommendation: **shared**, with `plugin_name` column in `events`. This mirrors agentaudit's current design.

2. **Does the SDK provide its own logging, or rely on stdlib logging?**
   - Current recommendation: stdlib logging, but provide a `sdk.log.get_logger(plugin_name)` helper that configures a sensible default (file handler at `<plugin_dir>/<plugin_name>.log`, rotating at 10MB).

3. **How does the SDK handle plugin versions colliding (e.g., two plugins declare the same namespace)?**
   - Current recommendation: `discover_plugins()` raises `DuplicatePluginError` with the two offending manifest paths. Loud failure is better than silent.

4. **Do we support Python 3.10?**
   - Current recommendation: no — 3.11+ for `tomllib`, `StrEnum`, better Pydantic v2 compat. Matches agentwiki-cc's existing requirement.

5. **Do we support Windows at v0.1?**
   - Current recommendation: best-effort. `os.replace` works; avoid `fcntl`. Document any Unix-only edges. Windows CI is out of scope for v0.1.

6. **Do we provide a "just use system Python" path AND a "managed venv" path?**
   - Current recommendation: both. `sdk.install.venv` is optional. Plugins that want isolation use it; plugins that don't, don't.

Document your decisions on each of these in `contract/README.md` before shipping v0.1.

---

## 11. Non-goals for v0.1

Things that are deliberately NOT in scope:

- Real-time push / streaming. The SDK is local-only. Push is the sidecar's job.
- Encryption at rest. `agentaudit-cc` has encryption (SQLCipher). The SDK does not. Plugins that want encryption can wrap the connection.
- Policy evaluation engine. That's in `agentaudit-cc/src/agentaudit/policy.py`. The SDK defines *where policy files live* but doesn't execute them.
- Neo4j projection. Stays in agentaudit-cc.
- Memory autoload / injection logic. Stays in agentmemory-cc. The SDK defines the manifest format; the plugin decides how to use it.
- Wiki graph building. Stays in agentwiki-cc.
- Remote push-down receiver. That's the sidecar.
- MDM deployment. Out of scope for OSS.
- Any TypeScript / Node code. Pure Python.

---

## 12. Reference reading: how a plugin uses this SDK

Once M10 ships, a conformant plugin looks like this (this is the target, not something to build now):

```python
# my_plugin/hook.py
from nativeagents_sdk.hooks import HookDispatcher, PreToolUseInput

dispatcher = HookDispatcher(plugin_name="my-plugin")

@dispatcher.on("PreToolUse")
def on_pre_tool_use(event: PreToolUseInput, ctx):
    ctx.log.info(f"About to call {event.tool_name}")
    ctx.write_audit({
        "event_type": "my_plugin.observation",
        "tool": event.tool_name,
    })

if __name__ == "__main__":
    dispatcher.run()
```

```toml
# my_plugin/plugin.toml
schema_version = 1

[plugin]
name = "my-plugin"
version = "0.1.0"
description = "A minimal plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = []
cli_entry = "my_plugin.cli:app"
```

```bash
# my_plugin/hooks/hook.sh (generated from SDK template)
#!/usr/bin/env bash
exec "$MY_PLUGIN_PYTHON" -m my_plugin.hook
```

```python
# install.py (run once)
from nativeagents_sdk.install import register_plugin
from nativeagents_sdk.plugin.manifest import load_plugin_manifest
from pathlib import Path

register_plugin(
    manifest=load_plugin_manifest(Path("plugin.toml")),
    hook_script=Path("hooks/hook.sh"),
)
```

That's the whole surface area. Everything else (hash chains, audit writes, hook parsing, Claude settings merge) is done by the SDK.

---

## 13. Handoff notes for the implementer

- **Read `spec.md` next.** It has the concrete details — exact DDL, exact JSON schemas, exact TOML shapes.
- **Read `successcriteria.md` third.** It has the checklist for "am I done with this milestone?"
- **Commit frequently.** One commit per milestone minimum. Include test output in the commit message for each milestone so future-you (or future-me) can audit.
- **Do not skip tests.** The SDK is infrastructure — its correctness is paramount. Slow down.
- **Flag ambiguities immediately.** If the spec is unclear or the existing repos contradict each other, write a comment in `contract/README.md` under "Open Questions" and pick a default. Don't block waiting for human input — just document the decision so it can be revisited.
- **Run the existing plugins' tests after extraction.** Once M2 is done, a quick sanity check: does `agentaudit-cc`'s existing test suite still pass if you port its `write_event` calls to use `nativeagents_sdk.audit.write_event`? (You don't have to actually refactor the plugin — just mentally verify the API shape matches.)
- **The spec is a living document.** Expect to update `spec.md` as you implement. Every contradiction between code and spec is a bug — resolve it in the spec first, then code to match.

Good luck. Build the SDK first, build it well, and everything else follows.
