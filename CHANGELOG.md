# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.0] - 2026-04-19

### Added (additive — no breaking changes to v0.1 public API)

- **`--version` / `-V` flag** on the `nativeagents-sdk` CLI — `nativeagents-sdk --version` now prints the SDK version and exits (uses Typer's eager callback pattern).
- **`pyproject.toml` classifiers** — added `Environment :: Console`, `Operating System :: MacOS`, `Operating System :: POSIX :: Linux`, `Topic :: Software Development :: Libraries :: Python Modules`.
- **CI badge** in README.
- `audit.chain`: `ChainSpec` dataclass, `compute_row_hash(row_fields, spec)`,
  `SDK_CHAIN_SPEC`. Plugins that maintain their own hash-chained event tables
  (e.g. `agentaudit-cc`) import this primitive and define a plugin-local
  `ChainSpec` instead of reimplementing SHA-256 canonical hashing. See
  `contract/03-audit-schema.md` for the two-store model.
- `policy`: new package with `Matcher` (static) and `MatchMode` (StrEnum).
  Lifts the four match-mode primitives (`contains`, `regex`, `glob`, `shell`)
  from `agentaudit-cc` into the SDK so all plugins share one implementation.
  Policy *definitions* (YAML, rule evaluation, violation projection) stay in
  each plugin. See `contract/12-policy.md`.
- `paths.deprecated_env_path(legacy_var, default, removal_version)`: helper
  for plugins migrating from plugin-specific env vars (e.g. `AGENTAUDIT_HOME`)
  to `NATIVEAGENTS_HOME`. Emits `DeprecationWarning` when the legacy var is
  set. Legacy-var support will be removed at SDK v0.3.0.
- `install.write_decision_shim(plugin_name, python_executable, module, dest)`:
  fills the SDK's `hooks/template.sh` for decision-path plugins (agentmemory,
  agentwiki). Returns the written path with execute bits set.
- `install.write_capture_shim(plugin_name, python_executable, spool_dir,
  drain_module, dest, daemon_sock=None)`: writes a 3-tier capture shim
  (daemon socket → atomic spool → background drain) for capture-path plugins
  (agentaudit). Always exits 0.
- `install.shim_is_executable(path)`: utility to check owner-execute bit.
- `contract/12-policy.md`: new canonical contract for the policy DSL matcher.
- `contract/03-audit-schema.md`: ChainSpec two-store model documentation.

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

[Unreleased]: https://github.com/nativeagents/nativeagents-sdk-py/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/nativeagents/nativeagents-sdk-py/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nativeagents/nativeagents-sdk-py/releases/tag/v0.1.0
