# Contract 01: Directory Layout

**Status**: Canonical  
**Last updated against spec version**: 0.1.0  
**Schema version**: 1

## Root: `~/.nativeagents/`

Resolved from `NATIVEAGENTS_HOME` env var (default: `~/.nativeagents`).

```
~/.nativeagents/
├── config.yaml                      # global config; SDK-owned
├── audit.db                         # shared SQLite audit store; SDK-owned
├── audit.db-wal                     # SQLite WAL file
├── audit.db-shm                     # SQLite shared-memory file
├── meta.json                        # SDK-owned metadata
│
├── memory/                          # agentmemory plugin namespace
│   ├── manifest.json
│   ├── core/
│   ├── relationship/
│   ├── projects/
│   ├── procedures/
│   ├── working/
│   └── reference/
│
├── wiki/                            # agentwiki plugin namespace
│   ├── graph.db
│   ├── pages/
│   ├── raw-inbox/
│   └── index.json
│
├── policies/
│   ├── local/
│   ├── pushed/
│   └── active/
│
├── spool/
│   └── <plugin_name>/
│       └── <kind>/
│
├── plugins/
│   └── <plugin_name>/
│       ├── plugin.toml
│       ├── logs/
│       └── <state>
│
└── bin/
```

## Ownership rules

- **SDK-owned**: `config.yaml`, `audit.db`, `meta.json`, `policies/`, `spool/`, `bin/`
- **Plugin-owned**: `memory/`, `wiki/`, `plugins/<name>/`
- **Shared-write**: `audit.db` via `write_event()` API only

## Mode requirements

- All top-level SDK directories: mode `0700`
- `audit.db`: mode `0600`
- Plugin directories: inherit from `plugins/`
