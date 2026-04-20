# nativeagents-sdk-py

**Shared contract and primitives for the Native Agents plugin ecosystem.**

This is the foundation layer for Claude Code plugins that participate in the
Native Agents ecosystem. It provides:

1. **Written specification** — the `contract/` directory defines all file formats,
   directory layouts, SQLite schemas, and plugin protocols.
2. **Reference Python implementation** — `nativeagents_sdk` library with helpers for
   config, audit, memory manifest, hooks, spool, and plugin installation.
3. **Conformance tooling** — `nativeagents-sdk validate-plugin` to verify a plugin
   meets the SDK contract.

## Requirements

- Python **3.11+** (macOS and Linux)

## Installation

```bash
pip install nativeagents-sdk
```

## Quick start

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

## Scaffold a new plugin

```bash
nativeagents-sdk init-plugin my-plugin
cd my-plugin
pip install -e ".[dev]"
pytest
```

## Contract documentation

See [`contract/`](contract/README.md) for the canonical specification.

## Examples

See [`examples/minimal_plugin/`](examples/minimal_plugin/) for a complete
reference plugin implementation.

## Design principles

- **No surprise I/O**: functions never write to disk unless explicitly asked
- **Idempotency everywhere**: register/unregister are safe to run N times
- **Hooks never block**: plugin errors are logged, not propagated to Claude Code
- **Audit writes are append-only**: SHA-256 hash chain enforces tamper evidence
- **No deps beyond the essentials**: pydantic, pyyaml, typer, rich, tomli-w

## License

MIT — see [LICENSE](LICENSE).
