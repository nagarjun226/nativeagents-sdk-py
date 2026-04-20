# Contract 10: Versioning and Schema Evolution

**Status**: Canonical  
**Last updated against spec version**: 0.1.0

## SDK versioning

SemVer. Pre-1.0: breaking changes permitted with CHANGELOG.md documentation.

## On-disk schema versions

Every on-disk format carries `schema_version`:
- `audit.db` — `meta.schema_version` row; current = 1
- `config.yaml` — top-level `schema_version`; current = 1
- `manifest.json` — top-level `schema_version`; current = 1
- `plugin.toml` — top-level `schema_version`; current = 1

## Forward compatibility rules

Readers MUST:
- Ignore unknown fields
- Reject `schema_version > MAX_SUPPORTED` with a clear error
- Accept `schema_version < CURRENT` if a migration path exists

## Migration rules

- Forward migration: SDK MAY migrate older formats automatically at startup
- Backward migration: NOT supported
- Migration functions: `audit/migrations.py` (SQLite), others TBD

## Reserved identifiers

- Field names starting with `_` are reserved for SDK internal use
- Plugin names starting with `native-`, `sdk-`, `system-` are reserved
- Event type prefixes `sdk.`, `system.`, `audit.` (without plugin prefix) are reserved
