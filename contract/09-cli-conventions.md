# Contract 09: CLI Conventions

**Status**: Canonical  
**Last updated against spec version**: 0.1.0

## SDK CLI

Entry point: `nativeagents-sdk`

Subcommands:
- `nativeagents-sdk version` — SDK version
- `nativeagents-sdk init-plugin <name>` — scaffold a new plugin
- `nativeagents-sdk validate-plugin [path]` — run conformance checks
- `nativeagents-sdk check-contract` — doctor all installed plugins

## Plugin CLI conventions

Each plugin SHOULD expose a CLI named after itself with these subcommands:
- `<plugin> version` — plugin + SDK version
- `<plugin> doctor` — health check (uses SDK `doctor()`)
- `<plugin> show` — display current state
- `<plugin> init` — interactive setup

## Output conventions

- Human-readable to stdout
- Errors to stderr
- Support `--json` flag for machine-readable output where relevant

## Exit codes

- `0` — success
- `1` — generic failure
- `2` — explicit block (hooks only)
- `3` — conformance violation
- `4` — integrity violation
