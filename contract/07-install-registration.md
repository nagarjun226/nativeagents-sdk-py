# Contract 07: Install Registration

**Status**: Canonical  
**Last updated against spec version**: 0.1.0

## ~/.claude/settings.json shape

```json
{
  "hooks": {
    "PreToolUse": [
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
    ]
  }
}
```

The `nativeagents_plugin` field identifies SDK-managed entries.

## Registration algorithm

1. Read settings (or `{"hooks": {}}`)
2. Backup to `settings.json.bak.<timestamp>`
3. For each event in `manifest.hooks`:
   - Skip if `nativeagents_plugin == plugin_name` already present (idempotent)
   - Append new entry with `nativeagents_plugin` marker
4. Atomic write

## Unregistration

Remove all entries where `nativeagents_plugin == plugin_name`. Prune empty arrays.
Does NOT delete plugin state directories.

## Idempotency guarantee

`register_plugin()` N times = same as once.
`unregister_plugin()` of non-registered plugin = no-op.
