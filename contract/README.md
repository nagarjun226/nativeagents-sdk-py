# Native Agents SDK — Contract Documents

This directory contains the canonical specification for the Native Agents plugin ecosystem.

The contract documents are the source of truth. The Python SDK in `src/nativeagents_sdk/`
is the reference implementation.

## Documents

| File | Topic |
|------|-------|
| [01-directory-layout.md](01-directory-layout.md) | `~/.nativeagents/` directory structure |
| [02-plugin-manifest.md](02-plugin-manifest.md) | `plugin.toml` format |
| [03-audit-schema.md](03-audit-schema.md) | SQLite audit schema and hash chain |
| [04-memory-manifest.md](04-memory-manifest.md) | Memory `manifest.json` and frontmatter |
| [05-hooks.md](05-hooks.md) | Hook script contract |
| [06-spool.md](06-spool.md) | Atomic-rename spool format |
| [07-install-registration.md](07-install-registration.md) | `~/.claude/settings.json` merge rules |
| [08-config.md](08-config.md) | `config.yaml` format |
| [09-cli-conventions.md](09-cli-conventions.md) | CLI naming and subcommand conventions |
| [10-versioning.md](10-versioning.md) | Schema evolution and versioning rules |
| [11-conformance.md](11-conformance.md) | Conformance harness checks and failure messages |

## Open Questions

### OQ-001: Shared vs. per-plugin audit.db

**Decision**: Shared `audit.db` (one database for all plugins).
- Pro: Cross-plugin correlation in a single query; sidecar tails one file.
- Pro: Matches agentaudit-cc's existing design.
- Con: Write contention (mitigated by SQLite WAL mode).

### OQ-002: Logging approach

**Decision**: stdlib `logging`. Plugins call `sdk.hooks.dispatcher._get_plugin_logger(plugin_name, logs_dir)` which returns a configured `RotatingFileHandler` logger.

### OQ-003: Duplicate plugin names

**Decision**: `discover_plugins()` raises `DuplicatePluginError` with both offending paths. Loud failure is better than silent incorrect behavior.

### OQ-004: Python version minimum

**Decision**: Python 3.11+. Provides `tomllib` in stdlib, `StrEnum`, better Pydantic v2 compat.

### OQ-005: Windows support at v0.1

**Decision**: Best-effort. `os.replace()` is cross-platform; no `fcntl` used anywhere. Windows CI is out of scope for v0.1 but not broken by design.

### OQ-006: System Python vs. managed venv

**Decision**: Both are supported. `install.venv` provides helpers for managed venvs; plugins that don't need isolation can use system Python directly.
