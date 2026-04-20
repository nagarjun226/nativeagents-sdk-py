# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-19

### Added
- Initial release of the Native Agents SDK.
- `paths` module: home directory resolution, plugin path helpers, atomic write, plugin name validation.
- `config` module: `Config` pydantic model, `load_config`, `save_config`, `validate_config`.
- `schema.events`: full hook event model hierarchy ported from agentaudit-cc.
- `schema.audit`: `AuditEvent` pydantic model.
- `schema.manifest`: `MemoryFile` and `Manifest` pydantic models.
- `schema.frontmatter`: `Frontmatter` pydantic model.
- `schema.plugin`: `PluginManifest` and `PluginRequires` pydantic models.
- `audit` module: `open_store`, `write_event`, `read_events`, `get_last_hash`, `verify_integrity`.
- `audit.migrations`: schema migration framework, `CURRENT_SCHEMA_VERSION = 1`.
- `memory` module: `load_manifest`, `save_manifest`, `rebuild_manifest`, `parse_frontmatter`, `render_frontmatter`.
- `hooks` module: `HookDispatcher`, `HookContext`, `HookDecision`, `read_hook_input`.
- `spool` module: `Spool` class with atomic-rename write.
- `install` module: `register_plugin`, `unregister_plugin`, `is_registered`, `doctor`.
- `plugin` module: `load_plugin_manifest`, `save_plugin_manifest`, `discover_plugins`, `resolve_plugin`.
- `cli`: `nativeagents-sdk` CLI with `init-plugin`, `validate-plugin`, `check-contract`, `version`.
- `conformance` module: `run_conformance`, `ConformanceReport`.
- Full test suite with `pytest` and property-based tests via Hypothesis.
- CI on Python 3.11 and 3.12, Ubuntu and macOS.
- `contract/` directory with 10 canonical specification documents.
- `examples/minimal_plugin/` reference implementation.

### Design decisions
- Shared `audit.db` (not per-plugin): enables cross-plugin correlation, matches agentaudit-cc design.
- stdlib `logging` with a `get_logger(plugin_name)` helper.
- `DuplicatePluginError` raised by `discover_plugins()` when two plugins share a name.
- Python 3.11+ only: leverages `tomllib` in stdlib, `StrEnum`, better Pydantic v2 compat.
- Windows: best-effort via `os.replace()` for atomic renames; no `fcntl` used.
