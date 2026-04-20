# Contract 08: Config File

**Status**: Canonical  
**Last updated against spec version**: 0.1.0  
**Schema version**: 1  
**File**: `~/.nativeagents/config.yaml`

## Format

```yaml
schema_version: 1

logging:
  level: INFO       # DEBUG | INFO | WARNING | ERROR
  directory: ~/.nativeagents/logs

audit:
  enabled: true
  verify_on_startup: false

plugins:
  my-plugin:
    key: value      # plugin-defined; SDK does not validate

sidecar:
  enabled: false    # reserved
```

## Behavior

- Missing file → return `Config()` with all defaults (never write)
- Unknown top-level keys → ignored (forward compat)
- `schema_version > 1` → raise `ConfigError`
