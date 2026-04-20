# Contract 06: Spool Format

**Status**: Canonical  
**Last updated against spec version**: 0.1.0

## Directory layout

```
~/.nativeagents/spool/<plugin_name>/<kind>/
├── .tmp/           # incomplete writes
├── 2026-04-19T14-30-00.123456+00-00-<8hex>.bin
└── ...
```

## Filenames

`<iso-timestamp-colons-replaced-by-dashes>-<8-char-random>.bin`

Sorted lexicographically = chronological order.

## Write algorithm

1. Write to `.tmp/<pid>-<random>.bin`
2. `fsync`
3. `os.replace()` to final name

## Consume algorithm

Consumers MUST be idempotent (crash between handle and unlink = replay on restart).

## Content format

Opaque bytes. Conventions:
- `audit` kind: UTF-8 JSON, one event per file
- `inbox` kind: MIME-typed or raw markdown
- `outbound` kind: future, defined by sidecar
