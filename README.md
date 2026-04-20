# nativeagents-sdk-py

[![CI](https://github.com/nativeagents/nativeagents-sdk-py/actions/workflows/ci.yml/badge.svg)](https://github.com/nativeagents/nativeagents-sdk-py/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-314%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](tests/)

**Canonical SDK for Claude Code plugins: shared contract, Python helpers, and conformance validation.**

Build Claude Code plugins that integrate reliably with the NativeAgents ecosystem.
The SDK gives you:

- **Written contract** — the `contract/` directory specifies file formats, directory layouts, SQLite schemas, and hook protocols every NativeAgents plugin must follow.
- **Python library** — `nativeagents_sdk` with helpers for canonical paths, SHA-256 audit chains, policy matching, and hook shim generation.
- **Conformance CLI** — `nativeagents-sdk validate-plugin .` runs 6 checks (manifest, reserved names, SDK version, hooks, shim) so you know your plugin is spec-compliant before release.

Used by:
**[AgentAudit-CC](https://github.com/nativeagents/agentaudit-cc)** · **[AgentMemory-CC](https://github.com/nativeagents/agentmemory-cc)** · **[AgentWiki-CC](https://github.com/nativeagents/agentwiki-cc)**

---

## Requirements

- Python **3.11+** (macOS and Linux)

## Quick Start

```bash
pip install nativeagents-sdk

# Scaffold a new plugin, run its tests, and verify conformance
nativeagents-sdk init-plugin my-plugin
cd my-plugin
pip install -e ".[dev]"
pytest
nativeagents-sdk validate-plugin .
```

Use the SDK primitives in your plugin:

```python
from nativeagents_sdk.hooks import HookDispatcher, HookDecision, PreToolUseInput

dispatcher = HookDispatcher(plugin_name="my-plugin")

@dispatcher.on("PreToolUse")
def on_pre(event: PreToolUseInput, ctx) -> HookDecision:
    ctx.log.info(f"Tool: {event.tool_name}")
    ctx.write_audit("my-plugin.pre_tool_use", {"tool": event.tool_name},
                    session_id=event.session_id)
    return HookDecision.ok()

if __name__ == "__main__":
    dispatcher.run()
```

## What's in the SDK

| Module | Purpose |
|--------|---------|
| `nativeagents_sdk.paths` | Canonical directory layout (`~/.nativeagents/`), `ensure_layout`, `atomic_write` |
| `nativeagents_sdk.audit.chain` | SHA-256 hash chain: `compute_row_hash`, `verify_chain`, `backfill_chain` |
| `nativeagents_sdk.policy` | YAML policy rule matching: `Matcher` with contains/regex/glob/shell modes |
| `nativeagents_sdk.install` | `write_decision_shim`, `write_capture_shim`, `register_plugin`, `unregister_plugin` |
| `nativeagents_sdk.conformance` | `run_conformance(plugin_dir)` — 6-check conformance runner |
| `nativeagents_sdk.schema.events` | `HOOK_INPUT_MODELS` — Pydantic models for all 10 Claude Code hook event types |

## Contract documentation

See [`contract/`](contract/README.md) for the canonical specification covering directory layout,
plugin manifest format, audit schema, hook protocol, spool format, and versioning.

## Examples

See [`examples/minimal_plugin/`](examples/minimal_plugin/) for a complete
reference plugin implementation.

## Design principles

- **No surprise I/O**: functions never write to disk unless explicitly asked
- **Idempotency everywhere**: register/unregister are safe to run N times
- **Hooks never block**: plugin errors are logged, not propagated to Claude Code
- **Audit writes are append-only**: SHA-256 hash chain enforces tamper evidence
- **No deps beyond the essentials**: pydantic, pyyaml, typer, rich, tomli-w

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All PRs must pass `pytest`, `ruff check`, and `mypy --strict`.

## License

MIT — see [LICENSE](LICENSE).
