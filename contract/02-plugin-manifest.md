# Contract 02: Plugin Manifest

**Status**: Canonical  
**Last updated against spec version**: 0.1.0  
**Schema version**: 1  
**File**: `plugin.toml` at plugin root; copied to `~/.nativeagents/plugins/<name>/plugin.toml` at install time.

## Format

```toml
schema_version = 1

[plugin]
name = "my-plugin"            # Required; ^[a-z][a-z0-9-]{0,39}$
version = "0.1.0"             # Required; SemVer
description = "..."           # Required

homepage = "https://..."      # Optional
license = "MIT"               # Optional, default MIT
authors = ["Name <email>"]    # Optional

well_known_namespace = "..."  # Only for first-party plugins (audit/memory/wiki)
hooks = ["PreToolUse"]        # Hook event names to register
owns_paths = [                # Paths claimed by this plugin
  "plugins/my-plugin/"
]
writes_audit_events = true    # Declares audit conformance requirement
produces_spool_kinds = ["audit"]
cli_entry = "my_plugin.cli:app"
hook_module = "my_plugin.hook"
min_sdk_version = "0.1.0"
max_sdk_version = "1.0.0"

[plugin.requires]
optional = ["agentmemory"]
required = []
```

## Validation rules

- `name` MUST match `^[a-z][a-z0-9-]{0,39}$`
- `name` MUST NOT be in: `audit`, `memory`, `wiki`, `policies`, `plugins`, `spool`, `bin`, `sidecar`, `config`, `meta`, `system`
- `hooks` entries MUST be valid Claude Code hook event names
- `owns_paths` MUST be within plugin namespace (unless `well_known_namespace` is set)
- `schema_version` MUST be 1
