# Contract 12: Policy DSL Matcher

**Status**: Canonical  
**Last updated against spec version**: 0.2.0

## Purpose

The SDK owns the *match primitives* used in plugin policy rules.
Policy *definitions* (YAML detector files, rule evaluation, violation
projection) stay in the plugins that author them.

## Public API

```python
from nativeagents_sdk.policy import Matcher, MatchMode
```

## MatchMode enum

| Value | String | Meaning |
|---|---|---|
| `MatchMode.CONTAINS` | `"contains"` | Substring present in field value |
| `MatchMode.REGEX` | `"regex"` | Python `re.search` with `re.MULTILINE` |
| `MatchMode.GLOB` | `"glob"` | `pathlib.PurePosixPath.match` + `fnmatch` fallback |
| `MatchMode.SHELL` | `"shell"` | `shlex`-parsed argv inspection |

## Match spec format

Each spec dict has exactly one mode key plus an optional `why` string:

```yaml
# Contains
- contains: "rm -rf"
  why: "destructive rm"

# Regex (re.MULTILINE by default; add dotall: true for re.DOTALL)
- regex: 'rm\s+(?:-[rRf]+\s+)+'
  why: "rm with recursive/force flags"

# Glob
- glob: "**/.env"
  why: "dotenv file"

# Shell (shlex-parsed argv)
- shell:
    program: rm
    args_contain: ["-r", "-rf", "-R"]
  why: "rm with recursive flag"
```

Bare strings are backward-compatible `contains` (no mode key required):

```yaml
command:
  - "rm -rf"    # same as contains: "rm -rf"
```

## Matcher static methods

### `Matcher.match_spec(spec, field, value) -> str | None`

Evaluate one spec dict against a string value.
Returns a human-readable reason string on match; `None` otherwise.

### `Matcher.match_tool_name(pattern, tool_name) -> bool`

Check whether a tool name satisfies a pattern (string or list).
Glob wildcards (`*`, `?`) are supported for MCP tool matching:
`mcp__*__delete_*` matches any MCP delete tool.

### `Matcher.match_inputs(patterns, tool_input) -> str | None`

Check all fields in `patterns` against `tool_input`.
Returns the first match reason or `None`.

`patterns` format: `{field_name: [spec, ...], ...}`.

## Integration with plugin policy rules

Plugins load their YAML detector files, call `Matcher.match_inputs` per
field, and own the violation projection logic.  Only the four match-mode
primitives live in the SDK.

## See also

`src/nativeagents_sdk/policy/matcher.py` — reference implementation  
`agentaudit-cc/src/agentaudit/policy.py` — reference plugin usage
