# Contract 11: Conformance Harness

**Status**: Canonical  
**Last updated against spec version**: 0.1.0

## Purpose

The conformance harness verifies that a plugin correctly implements the SDK contract.
Third-party plugin authors run it before claiming SDK compatibility.

## Invocation

```bash
nativeagents-sdk validate-plugin <plugin-dir>
nativeagents-sdk validate-plugin <plugin-dir> --json
```

Exit codes:
- `0` — all checks pass
- `1` — one or more checks failed

## Checks (in execution order)

| # | Name | Description | Hard / Soft |
|---|------|-------------|-------------|
| 1 | `plugin_toml_exists` | `plugin.toml` present and readable | Hard |
| 2 | `manifest_valid` | `plugin.toml` parses without error and passes schema validation | Hard |
| 3 | `name_not_reserved` | Plugin `name` is not in the reserved set | Hard |
| 4 | `sdk_version_satisfied` | `min_sdk_version <= nativeagents_sdk.__version__` | Hard |
| 5 | `hooks_known` | Every event in `hooks` is a recognised hook event type | Hard |
| 6 | `hook_script_exists` | `hooks/hook.sh` (or the file declared in manifest) exists and is executable | Hard |

### Planned checks (added as features mature)

| # | Name | Description |
|---|------|-------------|
| 7 | `dry_run_each_hook` | Import `hook_module`, dispatch a synthetic payload for each declared hook, assert no crash and one audit row + one spool file written |
| 8 | `chain_verifies` | Hash chain on the plugin's events verifies end-to-end after dry-run |
| 9 | `owns_paths_isolation` | Plugin did not write outside its `owns_paths` namespace during dry-run |
| 10 | `cli_entry_exits_zero` | If `cli_entry` is declared, `python -m <cli_entry> --help` exits 0 in ≤ 2 s |

## Report format

### Human-readable

```
Conformance report for: examples/minimal_plugin/
  ✅ plugin_toml_exists — plugin.toml found and readable
  ✅ manifest_valid — manifest parsed OK (name=minimal-plugin v0.1.0)
  ✅ name_not_reserved — name 'minimal-plugin' is not reserved
  ✅ sdk_version_satisfied — min_sdk_version=0.1.0 <= 0.1.0
  ✅ hooks_known — PreToolUse, PostToolUse are recognised events
  ✅ hook_script_exists — hooks/hook.sh is present and executable

6/6 checks passed.
```

### JSON (`--json`)

```json
{
  "plugin_dir": "examples/minimal_plugin",
  "passed": true,
  "checks": [
    {"name": "plugin_toml_exists", "passed": true, "message": "plugin.toml found and readable"},
    ...
  ]
}
```

## Failure messages

| Check | Failure message pattern |
|-------|------------------------|
| `plugin_toml_exists` | `plugin.toml not found in <dir>` |
| `manifest_valid` | `plugin.toml parse error: <detail>` |
| `name_not_reserved` | `Plugin name '<name>' is reserved` |
| `sdk_version_satisfied` | `Plugin requires SDK >= <ver>; installed <ver>` |
| `hooks_known` | `Unknown hook event '<name>'; expected one of: ...` |
| `hook_script_exists` | `Hook script <path> not found or not executable` |

## Relation to other contracts

- Check 1–2 delegate to [02-plugin-manifest.md](02-plugin-manifest.md).
- Check 7 depends on [03-audit-schema.md](03-audit-schema.md) and [06-spool.md](06-spool.md).
- Check 8 depends on the hash chain rules in [03-audit-schema.md](03-audit-schema.md).
- Check 9 depends on `owns_paths` rules in [01-directory-layout.md](01-directory-layout.md).
