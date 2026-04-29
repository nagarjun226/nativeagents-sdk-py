# minimal-plugin

Reference implementation for the [nativeagents-sdk](https://github.com/nativeagents/nativeagents-sdk-py).
Copy this as the starting point for your own plugin.

## What it does

Hooks into every Claude Code tool call and writes two audit events per invocation:

| Event | Trigger | Payload |
|-------|---------|---------|
| `minimal-plugin.pre_tool_use` | Before each tool call | `tool_name`, `input_keys` |
| `minimal-plugin.post_tool_use` | After each tool call | `tool_name`, `duration_ms` |

A one-liner is printed to stderr for each event so you can see it live in the Claude Code terminal.

## Install

```bash
# From the repo root
pip install nativeagents-sdk           # or: pip install -e .
nativeagents-sdk validate-plugin examples/minimal_plugin  # verify conformance first
```

After install, `~/.claude/settings.json` will contain hook entries that call the plugin for
`PreToolUse` and `PostToolUse` events.  Claude Code picks these up automatically on the next
session start — no restart required.

## Verify

```bash
nativeagents-sdk validate-plugin examples/minimal_plugin  # 6/6 checks, exit 0 = all pass
nativeagents-sdk check-contract                           # doctor checks across all plugins
```

## Audit events

Events are written to `~/.nativeagents/audit.db` under `plugin_name = "minimal-plugin"`.
Query them with any SQLite client:

```sql
SELECT sequence, event_type, payload_json, captured_at
FROM events
WHERE plugin_name = 'minimal-plugin'
ORDER BY sequence;
```

## Uninstall

Use `nativeagents_sdk.install.unregister_plugin("minimal-plugin")` programmatically,
or delete the hook entries manually from `~/.claude/settings.json`.

Your audit rows and any memory entries remain (user data is never deleted on uninstall).

## Structure

```
minimal_plugin/
├── plugin.toml          — manifest (name, version, hooks, …)
├── hooks/hook.sh        — generated wrapper script (do not edit)
├── src/minimal_plugin/
│   ├── __init__.py      — __version__
│   ├── hook.py          — PreToolUse + PostToolUse handlers  ← the interesting file
│   └── cli.py           — optional `minimal-plugin` CLI
├── tests/test_minimal.py
└── smoke.sh             — end-to-end smoke test
```
