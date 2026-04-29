# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | ✅ Active  |
| 0.1.x   | ⚠️ Critical fixes only |

## Scope

The NativeAgents SDK is a local library — it runs entirely on your machine. Relevant security concerns include:

- **Plugin registration**: `register_plugin` / `unregister_plugin` modify `~/.claude/settings.json` — the file that controls which hooks Claude Code runs
- **Hook shim generation**: `write_decision_shim` / `write_capture_shim` write executable shell scripts; always review generated scripts before installation
- **Audit database**: `write_audit()` appends to the plugin's SQLite database; contents may include user prompts, file paths, and command outputs — treat as sensitive PII
- **Dependency vulnerabilities**: Runtime dependencies include `pydantic`, `pyyaml`, `typer`, `rich`, `tomli-w`

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by:

1. Opening a **private** [GitHub Security Advisory](https://github.com/nativeagents/nativeagents-sdk-py/security/advisories/new)
2. Including: description of the vulnerability, steps to reproduce, potential impact, and (if known) a suggested fix

We will acknowledge receipt within 48 hours and aim to provide a fix or mitigation within 14 days for confirmed vulnerabilities.

## Security Best Practices for Plugin Authors

- **Never store secrets** in hook payloads or audit records — they may be logged verbatim
- **Validate all hook inputs** against the provided Pydantic models before processing
- **Hooks must always exit 0** — a crashing hook can expose internal state via stderr
- **Audit writes are append-only** — the SHA-256 hash chain detects tampering; do not bypass it
- **Review generated shims** — `write_decision_shim` produces synchronous hooks; ensure the called module cannot block indefinitely
