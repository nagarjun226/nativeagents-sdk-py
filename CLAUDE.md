# CLAUDE.md — nativeagents-sdk-py

Project context for Claude Code when working on the NativeAgents SDK.

## What this repo is

The shared foundation for NativeAgents Claude Code plugins. Provides canonical path management, audit chain hashing, policy matching, install helpers, and SDK conformance checks. Plugins import from this package — it has no direct Claude Code hook integration of its own.

Used by: AgentAudit-CC, AgentMemory-CC, AgentWiki-CC.

## Module map

| Module | Purpose |
|---|---|
| `nativeagents_sdk.paths` | `plugin_dir()`, `deprecated_env_path()`, canonical `~/.nativeagents/` layout |
| `nativeagents_sdk.audit.chain` | `compute_row_hash()`, `ChainSpec` — SHA-256 hash chain primitive |
| `nativeagents_sdk.policy` | `Matcher.match_tool_name()`, `Matcher.match_inputs()` — regex/glob/shell/contains |
| `nativeagents_sdk.install` | `write_decision_shim()`, `write_capture_shim()`, `register_plugin()`, `unregister_plugin()` |
| `nativeagents_sdk.conformance` | `run_conformance()` — 6-check plugin validator |
| `nativeagents_sdk.schema.events` | `HOOK_INPUT_MODELS` — Pydantic models for all 10 hook event types |

## Development setup

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests with coverage
.venv/bin/python -m pytest tests/ -v --cov=nativeagents_sdk --cov-fail-under=90
```

## Conventions

- Python 3.11+, fully type-annotated
- `ruff check src/ tests/ && ruff format --check src/ tests/` must pass clean
- Coverage must stay at ≥90% — the pyproject.toml `--cov-fail-under=90` enforces this
- All tests use `tmp_path` for path isolation
- Public API changes require updating `CHANGELOG.md`

## SDK conformance checks (6/6)

Plugins must pass all 6 checks from `run_conformance()`:
1. `plugin_toml_exists` — `plugin.toml` present in project root
2. `manifest_valid` — required fields: `name`, `version`, `description`, `hooks`
3. `name_not_reserved` — plugin name not in reserved list
4. `sdk_version_satisfied` — installed SDK meets plugin's minimum version
5. `hooks_known` — all declared hooks are in `VALID_HOOK_EVENTS`
6. `hook_script_exists` — declared hook script file exists on disk

## Valid hook events

```python
VALID_HOOK_EVENTS = {
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "SubagentStop", "Stop", "Notification", "PreCompact", "PostCompact", "SessionEnd"
}
```

Note: `CwdChanged` is NOT a valid hook event.

## Canonical path layout

```
~/.nativeagents/
├── plugins/
│   ├── agentaudit/
│   ├── agentmemory/
│   └── agentwiki/
└── settings.json  (managed by Claude Code, not SDK)
```
