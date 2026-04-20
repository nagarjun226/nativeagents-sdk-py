# Contract 05: Hook Script Contract

**Status**: Canonical  
**Last updated against spec version**: 0.1.0

## Hook script template

See `src/nativeagents_sdk/hooks/template.sh`.

Placeholders: `{{PLUGIN_NAME}}`, `{{PYTHON_EXECUTABLE}}`, `{{PYTHON_MODULE}}`

## Stdin payload

Claude Code writes JSON to stdin. Base shape:

```json
{
  "hook_event_name": "PreToolUse",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "permission_mode": "allow",
  "transcript_path": "..."
}
```

Event-specific extra fields: see `src/nativeagents_sdk/schema/events.py`.

## Exit codes

- `0` — success or non-fatal error (hooks NEVER block on errors)
- `2` — explicit policy block (Claude Code refuses to proceed)
- Any other non-zero — treated as error by Claude Code (avoid)

## Env vars

- `HOOK_EVENT_NAME` — preferred event type source
- `NATIVEAGENTS_HOME` — home dir override
- `CLAUDE_HOME` — Claude home override
- `NATIVEAGENTS_PLUGIN_NAME` — set by the template
