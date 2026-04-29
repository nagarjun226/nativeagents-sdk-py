# nativeagents-sdk-py — Success Criteria

> **Purpose of this document**
>
> `plan.md` says *what* to build and in *what order*.
> `spec.md` says *how* each piece must behave to be correct.
> **`successcriteria.md` (this file) says how we know we are done.**
>
> Every claim in this document is meant to be **objectively verifiable** — either by running a command, opening a file, or pointing at a passing CI job. If you (future implementer) cannot check off an item with evidence, the SDK is not ready. Ship-readiness is not a feeling.
>
> Read this end-to-end before you start M0. Then re-read the relevant section before closing each milestone. At the end of M10, the "Release readiness" section at the bottom must be entirely green before we tag `v0.1.0` and publish to PyPI.

---

## How to use this document

1. Each milestone (M0–M10) has its own block. Each block contains:
   - **Must pass** — hard acceptance criteria. If any fail, the milestone is not done.
   - **How to verify** — the exact command, file path, or observable behavior.
2. Items are phrased as checkboxes (`- [ ]`). Tick them off in a PR description or a scratch commit as milestones close. Do **not** move to the next milestone until all items in the current one are ticked.
3. The last three sections — **Cross-cutting quality gates**, **End-to-end acceptance tests**, **Release readiness checklist** — apply to the repo as a whole. They must all be green before `v0.1.0`.
4. If a criterion is ambiguous, the *verification command* wins. If the command doesn't exist yet, write it into the milestone instead of guessing.
5. Do not lower the bar by rewording criteria. If a criterion turns out to be wrong, open a PR that updates `spec.md`, `plan.md`, *and* this file together, with a note explaining why.

---

## Conventions used below

- **"Passes"** means exit code 0 and no warnings unless explicitly allowed.
- **"Covered"** means the behavior has at least one test that would fail if the behavior regressed. Not the same as "line coverage."
- **"Documented"** means there is a prose section in `README.md` or `contract/*.md` that a new engineer can read and apply without reading the source.
- **"Stable"** means running the command twice on a fresh checkout produces byte-identical output for deterministic artifacts (hashes, spool filenames given a fixed seed clock, generated configs).
- **"Reference plugin"** refers to `examples/sample-plugin/` produced in M10. Third-party authors will copy it as their starting point; if anything breaks there, it breaks for everyone.

---

## M0 — Repo scaffolding

**Goal of milestone** (recap from `plan.md`): a publishable Python package skeleton with CI hooked up, lint/type/test tooling in place, and a placeholder public import that works.

### Must pass

- [ ] Repo has the layout documented in `plan.md` §"Target repo layout":
  - [ ] `src/nativeagents_sdk/` package directory (PEP 621 src-layout).
  - [ ] `tests/` with at least one passing smoke test.
  - [ ] `contract/` directory present (even if only a README stub for now).
  - [ ] `examples/` directory present.
  - [ ] `pyproject.toml` at repo root declares `nativeagents-sdk` as the distribution name and `nativeagents_sdk` as the import package.
- [ ] `python -m pip install -e .[dev]` on a fresh virtualenv completes without warnings on Python 3.11 and 3.12 on macOS and Linux.
- [ ] `python -c "import nativeagents_sdk; print(nativeagents_sdk.__version__)"` prints a PEP 440-compliant version string matching `pyproject.toml`.
- [ ] `ruff check .` passes with zero findings.
- [ ] `ruff format --check .` passes with zero findings.
- [ ] `mypy --strict src/nativeagents_sdk` passes with zero findings.
- [ ] `pytest -q` runs the smoke test and reports `1 passed` (or more).
- [ ] GitHub Actions (or equivalent CI) is configured and green on `main` for the matrix `{python: [3.11, 3.12]} × {os: [ubuntu-latest, macos-latest]}`.
- [ ] `README.md` exists and contains (at minimum): one-paragraph positioning, install command, minimum supported Python, and a link to `contract/`.
- [ ] `LICENSE` file is present (Apache 2.0 or MIT — pick and commit).
- [ ] `.gitignore` excludes `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `dist/`, `build/`, `*.egg-info/`.

### How to verify

```bash
# From a fresh clone
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
ruff check . && ruff format --check .
mypy --strict src/nativeagents_sdk
pytest -q
python -c "import nativeagents_sdk; print(nativeagents_sdk.__version__)"
```

CI must show all steps green on both OSes and both Python versions.

---

## M1 — Paths & configuration

**Goal of milestone**: canonical `~/.nativeagents/` layout is represented in code; reads of `config.yaml` produce a validated typed object; no other module in the SDK ever builds paths by string concatenation again.

### Must pass

- [ ] `nativeagents_sdk.paths` module exports at minimum:
  - `root()` → `Path`
  - `audit_db()` → `Path`
  - `memory_dir()` → `Path`
  - `wiki_dir()` → `Path`
  - `policies_dir()` → `Path`
  - `spool_dir()` → `Path`
  - `plugin_dir(plugin_name: str)` → `Path`
  - `bin_dir()` → `Path`
  - `config_path()` → `Path`
- [ ] Every function above is covered by a test that asserts (a) the returned path is absolute, (b) it sits under `root()`, (c) it matches the layout in `spec.md` §"Canonical directory layout".
- [ ] `NATIVEAGENTS_HOME` environment variable overrides `root()` and is honored by every other path function. Test exists.
- [ ] Calling any path function **does not** create directories as a side-effect. A separate `ensure_layout()` function creates the full tree idempotently with mode `0o700` on the root.
- [ ] `nativeagents_sdk.config` exposes a Pydantic model `SDKConfig` with every field described in `spec.md` §"config.yaml", each with a default matching the spec.
- [ ] `load_config()` reads `config_path()`, merges defaults, validates, and returns `SDKConfig`. Missing file → returns defaults (not an error).
- [ ] `load_config()` raises `nativeagents_sdk.errors.ConfigError` (subclass of `ValueError`) on any validation failure, with a message that names the offending field.
- [ ] Fuzz test / property test: any config where a single field is randomly replaced with a wrong-typed value produces `ConfigError`, never a raw `pydantic.ValidationError` or `KeyError`.

### How to verify

```bash
pytest tests/test_paths.py tests/test_config.py -q
NATIVEAGENTS_HOME=/tmp/na-test python -c "from nativeagents_sdk import paths; print(paths.audit_db())"
# Expected: /tmp/na-test/audit.db
```

---

## M2 — Audit schema & SQLite writer

**Goal of milestone**: the SQLite audit store described in `spec.md` §"SQLite audit DDL + hash chain" exists as code; any plugin can append a row and the chain verifies; schema is version-tagged.

### Must pass

- [ ] `nativeagents_sdk.audit.schema` module exposes `SCHEMA_VERSION: int` and `DDL: str` containing the full `CREATE TABLE events (...)` from spec.
- [ ] `nativeagents_sdk.audit.store.AuditStore` class with at minimum:
  - `AuditStore(db_path: Path, plugin_name: str)` opens/creates the DB, applies migrations, verifies `schema_version` table matches `SCHEMA_VERSION`.
  - `append(event: AuditEvent) -> int` inserts a row, returns the new `id`, and enforces the hash chain atomically in a single transaction.
  - `verify_chain(session_id: str) -> bool` walks the chain for that session and returns True iff every `row_hash` matches the canonicalization rule.
  - `iter_events(since_id: int = 0) -> Iterator[AuditEvent]` yields events in insertion order.
- [ ] `AuditEvent` is a Pydantic model (v2) with every field from `spec.md` §"SQLite audit DDL" and validates `session_id` against the regex in `agentaudit-cc/src/agentaudit/schema.py` (reused constant).
- [ ] Hash chain canonicalization uses exactly `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` and SHA-256. A test vector file `tests/fixtures/hash_chain_vectors.json` exists and is checked against (regression fence).
- [ ] `schema_version` table is created, populated on first write, and a mismatch at open-time raises `SchemaVersionMismatch` (subclass of `RuntimeError`).
- [ ] WAL mode is enabled (`PRAGMA journal_mode=WAL`). Test asserts the pragma after open.
- [ ] Concurrent writers: a test spawns 4 threads each appending 250 rows for distinct sessions, then calls `verify_chain` on each session. All four chains verify. No "database is locked" surfaces to the caller.
- [ ] Same test but with 4 plugin processes (subprocesses) writing with the same `plugin_name`s to the same DB also verifies.
- [ ] Tamper detection test: mutate one row's `payload_json` directly via raw SQL, then `verify_chain` returns False **and** identifies which `id` broke the chain.
- [ ] Performance smoke: appending 10,000 events on a tmpfs takes < 5 seconds on CI (`pytest-benchmark` or timed test). If it doesn't, add an index or batched-commit setting; do not silently loosen the bar.
- [ ] `AuditStore` is safe to call from a signal handler (no non-reentrant primitives held across `append`). Documented in the module docstring.

### How to verify

```bash
pytest tests/test_audit_schema.py tests/test_audit_store.py tests/test_audit_chain.py -q
pytest tests/test_audit_concurrency.py -q  # 4-thread + 4-process
pytest tests/test_audit_perf.py -q --benchmark-only
```

---

## M3 — Memory manifest & reader

**Goal of milestone**: `~/.nativeagents/memory/` is a valid, plugin-agnostic library of memory files with a canonical manifest; any plugin can list, read, add, and remove entries without stepping on another plugin.

### Must pass

- [ ] `nativeagents_sdk.memory.manifest` module exposes:
  - `Manifest` Pydantic model matching `spec.md` §"Memory manifest".
  - `read_manifest(memory_dir: Path) -> Manifest` — returns empty manifest if file doesn't exist.
  - `write_manifest(memory_dir: Path, manifest: Manifest) -> None` — atomic (temp + `os.replace`).
  - `add_entry(memory_dir, entry: ManifestEntry) -> Manifest` — idempotent on `entry.id`.
  - `remove_entry(memory_dir, entry_id: str) -> Manifest` — no-op if missing.
- [ ] `ManifestEntry` has every field from spec (`id`, `name`, `description`, `type`, `file`, `source_plugin`, `created_at`, `updated_at`, plus any spec-mandated optional fields). `type` is a `Literal` of the enum defined in spec. Unknown types fail validation.
- [ ] YAML frontmatter reader/writer: given a memory file path, return `(frontmatter: dict, body: str)`; writer round-trips losslessly (test: read → write → read gives byte-identical file).
- [ ] Frontmatter schema is validated against the manifest entry shape; a memory file whose frontmatter disagrees with the manifest triggers `MemoryIntegrityError` with a message naming both sides of the disagreement.
- [ ] Locking: concurrent `add_entry` calls from two processes do not corrupt the manifest. Use an fcntl / portalocker lock on `memory/.manifest.lock` and test it with two subprocesses racing.
- [ ] `list_entries(memory_dir, *, plugin: str | None = None, type: str | None = None)` filters correctly. Covered by parameterized test.
- [ ] Migrating from agentmemory-cc's existing manifest format is either (a) automatic on first read or (b) documented as a one-time `nativeagents migrate-memory` CLI command. Pick one, implement it, test it against a fixture copied from agentmemory-cc.

### How to verify

```bash
pytest tests/test_memory_manifest.py tests/test_memory_frontmatter.py tests/test_memory_locking.py -q
python -c "from nativeagents_sdk.memory.manifest import read_manifest; print(read_manifest('$HOME/.nativeagents/memory'))"
```

---

## M4 — plugin.toml manifest

**Goal of milestone**: a single declarative file describes a plugin; the SDK can validate it, and every other subsystem (hook dispatcher, installer, CLI) reads the same object.

### Must pass

- [ ] `nativeagents_sdk.plugin.manifest` module exposes:
  - `PluginManifest` Pydantic model with every field documented in `spec.md` §"plugin.toml schema" (`name`, `version`, `description`, `authors`, `hooks`, `owns_paths`, `writes_audit_events`, `cli_entry`, `hook_module`, `min_sdk_version`, etc.).
  - `load_plugin_manifest(path: Path) -> PluginManifest`.
  - `validate_plugin_manifest(manifest: PluginManifest) -> None` — raises `PluginManifestError` on any violation.
- [ ] **Name validation**: `name` matches `^[a-z][a-z0-9-]{0,39}

 and is not in the reserved set (`audit, memory, wiki, policies, plugins, spool, bin, sidecar, config, meta, system`). Covered by a parameterized test with both positive and negative examples.
- [ ] **Version validation**: `version` is PEP 440. Invalid → `PluginManifestError`.
- [ ] **Hook validation**: every string in `hooks` is one of the seven Claude Code hook events enumerated in `spec.md`. Unknown events → error.
- [ ] **Namespace validation**: `owns_paths` entries resolve under `plugins/<name>/` or the well-known first-party carve-outs (`audit.db`, `memory/`, `wiki/`). A manifest that claims to own `/etc/passwd` or another plugin's dir → `PluginManifestError`.
- [ ] **SDK version gate**: `min_sdk_version` must be `<= nativeagents_sdk.__version__`. If greater, `load_plugin_manifest` raises `SDKVersionTooOld` with a clear upgrade message.
- [ ] TOML parser is `tomllib` on 3.11+; writes go through `tomli_w`. Writes are atomic.
- [ ] Round-trip test: write a manifest, read it back, compare model equality; passes for at least three fixture manifests (first-party reference plugin × 3).
- [ ] An "unknown field" in `[plugin]` table is tolerated with a logged warning (forward-compat). An unknown field under `[plugin.hooks]` or `[plugin.owns_paths]` is an error (stricter). Distinction is tested.
- [ ] Well-known namespace carve-outs (agentaudit → audit.db, agentmemory → memory/, agentwiki → wiki/) are encoded in code (not magic strings at call sites) and covered.

### How to verify

```bash
pytest tests/test_plugin_manifest.py tests/test_plugin_manifest_namespace.py -q
python -c "from nativeagents_sdk.plugin.manifest import load_plugin_manifest; print(load_plugin_manifest('examples/sample-plugin/plugin.toml'))"
```

---

## M5 — Hook dispatcher

**Goal of milestone**: a plugin author writes `@dispatcher.on("PreToolUse")` decorated functions and nothing else; stdin → JSON → typed model → their handler → exit code, all handled by the SDK.

### Must pass

- [ ] `nativeagents_sdk.hooks.dispatcher` module exposes `HookDispatcher` class as documented in `spec.md` §"Hook dispatcher Python API".
- [ ] Supported events: all seven from `HookEventType` enum in `agentaudit-cc/schema.py` (`SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, SubagentStop, Stop, Notification`). Every event has an input model extracted/imported verbatim.
- [ ] `@dispatcher.on("PreToolUse")` registers a handler. Registering two handlers for the same event in the same dispatcher is an error at import-time.
- [ ] `dispatcher.run()`:
  - Reads JSON from stdin.
  - Selects the input model by `hook_event_name`.
  - Constructs a `HookContext` with `plugin_name`, `plugin_dir`, `audit_db` (`AuditStore` bound to this plugin), `config` (typed `SDKConfig`), `log` (stdlib `logging.Logger` rooted at `nativeagents.<plugin_name>`), and `write_audit(event)`.
  - Invokes the handler, catches the result, converts to exit code per spec.
  - Unknown event → exit 0 with a debug log (not an error; newer Claude Code versions may add events).
- [ ] **Exit code contract** (matches `spec.md` §"Hook script contract"):
  - Handler returns `None` → exit 0.
  - Handler returns `Block(reason=...)` (or equivalent) → exit 2 with reason on stderr.
  - Handler raises → exit 1, traceback to stderr, event still written to audit with `status="error"`.
  - Handler takes longer than the per-event timeout from `config.yaml` → SIGTERM, exit code 124, event status = "timeout".
- [ ] **Isolation**: handler crash in plugin A cannot corrupt audit state for plugin B. Test: two dispatchers in one process, A raises, B's subsequent `write_audit` still succeeds and chain still verifies.
- [ ] **Malformed stdin**: invalid JSON → exit 1, message to stderr, nothing written to audit. Test covers.
- [ ] **Missing required fields**: Pydantic validation error → exit 1, message to stderr that names the missing field. Does not leak Pydantic internals to the user-facing message (wrap in `HookInputError`).
- [ ] **Observability**: each run emits one structured log line at INFO level summarizing `{plugin, event, duration_ms, status}`. Configurable log level via env var `NATIVEAGENTS_LOG_LEVEL`.
- [ ] **Performance**: round-trip (stdin read → handler no-op → audit row → exit) stays under 50ms on CI for a minimal handler. Benchmarked.

### How to verify

```bash
pytest tests/test_dispatcher.py tests/test_dispatcher_exit_codes.py tests/test_dispatcher_isolation.py -q
echo '{"hook_event_name":"PreToolUse","session_id":"s1","tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}' \
  | python -m nativeagents_sdk._test_dispatcher_noop   # included test script
echo $?  # must be 0
```

---

## M6 — Spool & hand-off

**Goal of milestone**: every audit row is also mirrored to a file in `~/.nativeagents/spool/` so the sidecar can ship it upstream; atomic rename semantics prevent partial reads; no data loss under crash.

### Must pass

- [ ] `nativeagents_sdk.spool` module exposes `SpoolWriter(spool_dir: Path, plugin_name: str)` with:
  - `write(event: AuditEvent) -> Path` — writes to `spool_dir/tmp/<uuid>.json` then `os.replace` into `spool_dir/<timestamp>_<session>_<sequence>_<plugin>.json`.
  - `rotate()` — no-op for MVP, but the method exists so we can evolve without API breakage.
- [ ] Filename format matches `spec.md` §"Spool format" exactly. A test asserts the regex.
- [ ] `os.replace` is used (not `shutil.move`), and the temp file is on the same filesystem as the destination. Covered by a test that mocks `os.replace` and asserts it was called.
- [ ] A sidecar-simulator test reads all spool files in timestamp order and confirms (a) no partial/corrupt JSON is ever observed, (b) the set equals the set of audit events appended, (c) the hash chain can be reconstructed from spool alone.
- [ ] **Crash test** (Linux-only, skipped on macOS): spawn a subprocess that `append`s 100 events then `SIGKILL` it mid-run; afterwards, number of spool files equals number of committed audit rows ± 0. No orphan `tmp/` files remain after a `SpoolWriter.startup_cleanup()` call (explicitly invoked at process start).
- [ ] Size caps: a config knob `spool.max_bytes_per_file` (default in spec) is enforced; oversize payloads are rejected with `SpoolPayloadTooLarge` (not silently truncated).
- [ ] The spool writer is **append-only** from the plugin side. Deletion is only done by `nativeagents_sdk.spool.cleanup.drop(path)` — a separate API the sidecar calls after successful upload. Plugins must not import it. Enforced via `__all__` and a `contract/spool.md` note.

### How to verify

```bash
pytest tests/test_spool.py tests/test_spool_atomic.py tests/test_spool_crash.py -q
ls ~/.nativeagents/spool/  # after running the dispatcher test, files should exist
```

---

## M7 — Install registration

**Goal of milestone**: `nativeagents install` wires a plugin into Claude Code's `~/.claude/settings.json` safely and reversibly; running it twice is a no-op.

### Must pass

- [ ] `nativeagents_sdk.install` module exposes:
  - `install_plugin(manifest: PluginManifest, plugin_source_dir: Path) -> InstallReport`
  - `uninstall_plugin(plugin_name: str) -> InstallReport`
  - `list_installed() -> list[PluginManifest]`
  - `verify_installation(plugin_name: str) -> list[Issue]` — returns diagnostics, empty list = healthy.
- [ ] Install copies the plugin's source tree into `~/.nativeagents/plugins/<name>/` (excluding `.venv/`, `__pycache__/`, etc.) and generates hook scripts into `~/.nativeagents/bin/` from the template in `spec.md` §"Hook script contract". Scripts are `chmod 0755`.
- [ ] Template placeholders (`{{PLUGIN_NAME}}`, `{{PYTHON_EXECUTABLE}}`, `{{PYTHON_MODULE}}`) are substituted. `PYTHON_EXECUTABLE` defaults to the absolute path of the interpreter the CLI is running under.
- [ ] Edits to `~/.claude/settings.json` are performed atomically (temp + `os.replace`) and use a **marker field** `"nativeagents_plugin": "<name>"` on each entry. Idempotency test: run `install_plugin` twice; resulting `settings.json` is byte-identical to after the first run.
- [ ] Before editing `settings.json`, a backup is written to `~/.claude/settings.json.bak.<timestamp>`, up to N=5 rolling backups retained.
- [ ] If `~/.claude/settings.json` doesn't exist, it's created with `{}` and then edited.
- [ ] If `settings.json` contains a hook entry that is **not** ours (no marker), it is preserved unchanged. Covered by a test with a hand-crafted `settings.json` containing a third-party entry plus one of ours.
- [ ] `uninstall_plugin` removes only entries whose `nativeagents_plugin` marker matches; leaves others intact. Covered.
- [ ] `uninstall_plugin` removes `~/.nativeagents/plugins/<name>/` and `~/.nativeagents/bin/<name>-*` scripts. Does **not** delete audit rows, memory entries, or wiki artifacts (user data survives uninstall by design). Covered.
- [ ] `verify_installation` detects and reports at minimum: missing hook script, unreadable `settings.json` entry, manifest/installed version mismatch, `min_sdk_version` now unsatisfied.
- [ ] Cross-platform: install path resolution uses `pathlib.Path.home()`; on Windows, `%USERPROFILE%\.claude\settings.json` is honored. (Even if we don't ship Windows in v0.1, the code must not hardcode `/Users` or `$HOME`.)

### How to verify

```bash
pytest tests/test_install.py tests/test_install_idempotent.py tests/test_install_preserves_foreign.py -q
nativeagents install examples/sample-plugin
nativeagents install examples/sample-plugin  # no-op, exit 0
diff ~/.claude/settings.json ~/.claude/settings.json.bak.*  # identical except for first install
nativeagents verify sample-plugin  # no issues
nativeagents uninstall sample-plugin
```

---

## M8 — CLI

**Goal of milestone**: `nativeagents` is a single typer-based CLI that wraps everything above with consistent output, exit codes, and `--json` mode for scripting.

### Must pass

- [ ] `nativeagents --help` lists at minimum: `install`, `uninstall`, `list`, `verify`, `init`, `doctor`, `migrate-memory`, `version`.
- [ ] Every subcommand has:
  - A one-line description in `--help`.
  - `--json` flag that emits machine-readable output on stdout, keeping human-readable output on stderr.
  - Exit code 0 on success, non-zero on failure. Exit codes are documented in `contract/cli.md`.
- [ ] `nativeagents version` prints `nativeagents-sdk <semver>` and the underlying Python version.
- [ ] `nativeagents init` creates `~/.nativeagents/` layout + default `config.yaml` idempotently. Safe to run on an existing install.
- [ ] `nativeagents doctor` checks: Python version, SDK version, layout integrity, audit DB schema version, hash chain verification for the last 100 events, plugin list health (`verify_installation` for each). Prints a grouped report; exits non-zero if any check fails.
- [ ] `nativeagents list` prints installed plugins with columns: `name, version, events, status`. `--json` emits a list of `PluginManifest` dicts plus status.
- [ ] CLI does not import heavy submodules at top of file; `nativeagents --help` returns in < 200ms on CI. Measured.
- [ ] Typer tab-completion script generation works (`nativeagents --show-completion bash` prints non-empty).
- [ ] Every CLI path is covered by a test using `typer.testing.CliRunner` — no subprocess-per-test tax on CI.

### How to verify

```bash
pytest tests/test_cli.py -q
nativeagents --help
nativeagents doctor
nativeagents list --json | jq .
time nativeagents --help   # < 200ms
```

---

## M9 — Conformance harness

**Goal of milestone**: there is a command — `nativeagents conformance <path-to-plugin>` — that emits a pass/fail report covering every contract the SDK defines. Third parties use it as a gate before claiming SDK compatibility.

### Must pass

- [ ] `nativeagents_sdk.conformance` module exposes `run_conformance(plugin_dir: Path) -> ConformanceReport` and a thin CLI wrapper.
- [ ] Checks performed (each is its own named check with pass/fail/skip + explanation):
  1. **manifest.toml present and valid** (delegates to M4).
  2. **name not reserved, SDK version satisfied**.
  3. **Every declared hook has a registered handler** (import `hook_module`, inspect `dispatcher._handlers`).
  4. **Dry-run each declared hook** with a synthetic input (from `tests/fixtures/hook_inputs/<event>.json`); handler must not crash, must return one of the documented result types, must write exactly one audit row + one spool file with correct plugin_name.
  5. **Hash chain on the plugin's events verifies** end-to-end after the dry-run pass.
  6. **`owns_paths` isolation**: the plugin did not write outside its declared namespace. Implemented via a temp HOME sandbox + a filesystem watcher (or inotify on Linux; on macOS use a manual `before/after` snapshot).
  7. **CLI entry point**: if `cli_entry` is declared, `python -m <cli_entry> --help` exits 0 in ≤ 2s.
  8. **`nativeagents uninstall` cleanly removes everything the plugin wrote** except user data.
- [ ] Report is printable as both human-readable table and `--json`.
- [ ] Exit code: 0 iff every check passes; 1 if any hard check fails; 2 if only soft checks warn.
- [ ] The reference plugin (`examples/sample-plugin`) passes all checks.
- [ ] A **deliberately broken** fixture plugin in `tests/fixtures/broken_plugin/` is shipped and tests assert the harness identifies *exactly* which check it fails (parameterized: one fixture per failure mode).

### How to verify

```bash
pytest tests/test_conformance.py -q
nativeagents conformance examples/sample-plugin    # exit 0
nativeagents conformance tests/fixtures/broken_plugin  # exit 1 with named failure
nativeagents conformance examples/sample-plugin --json | jq .passed
```

---

## M10 — Reference plugin & release

**Goal of milestone**: `examples/sample-plugin` is a working end-to-end plugin that a new author can copy in five minutes. The package is published to PyPI. Contract docs exist. We tag `v0.1.0`.

### Must pass — reference plugin

- [ ] Path: `examples/sample-plugin/`.
- [ ] ≤ 150 lines of Python across all files (keeps it readable).
- [ ] Declares 2 hooks (`PreToolUse`, `PostToolUse`) that log tool name + duration to audit and print a one-liner on stderr.
- [ ] Ships its own `README.md` that explains how to install, what it does, what audit events it emits, and how to uninstall.
- [ ] Passes `nativeagents conformance`.
- [ ] Works against a real Claude Code session: a manual test script in `examples/sample-plugin/smoke.sh` installs it, runs a scripted Claude Code session (or a recorded JSON replay into the dispatcher), and asserts audit rows exist.

### Must pass — contract docs

- [ ] `contract/README.md` — index, what each doc covers, which is load-bearing.
- [ ] `contract/layout.md` — canonical `~/.nativeagents/` tree, ownership rules, reserved names.
- [ ] `contract/plugin-manifest.md` — `plugin.toml` schema and examples.
- [ ] `contract/audit.md` — SQLite DDL, hash chain algorithm, canonicalization rule, a worked example.
- [ ] `contract/memory.md` — manifest format, frontmatter rules, locking.
- [ ] `contract/hooks.md` — seven events, dispatcher API, exit codes, timeouts.
- [ ] `contract/spool.md` — filename format, atomic rename rule, sidecar protocol.
- [ ] `contract/install.md` — `settings.json` edit rules, idempotency, uninstall semantics.
- [ ] `contract/cli.md` — every subcommand, exit codes, `--json` schema.
- [ ] `contract/conformance.md` — the checks run by the harness, what each failure means.
- [ ] Every doc has a "Last updated against spec version X.Y" line and matches the current `spec.md`.

### Must pass — release

- [ ] `CHANGELOG.md` has a `0.1.0` entry summarizing every milestone.
- [ ] `pyproject.toml` declares `classifiers`, `license`, `readme`, `urls.homepage`, `urls.source`, `urls.issues`.
- [ ] `python -m build` produces a sdist and a wheel without warnings.
- [ ] `twine check dist/*` passes.
- [ ] Publishing is driven by a tag-triggered GitHub Action that requires CI to be green.
- [ ] After a test publish to TestPyPI, `pip install -i https://test.pypi.org/simple nativeagents-sdk` succeeds in a fresh container; the reference plugin then installs and conforms from the published wheel.
- [ ] Git tag `v0.1.0` exists on `main`, matches `__version__`, signed (if a signing key is configured).

### How to verify

```bash
pytest -q                           # all tests green
python -m build
twine check dist/*
nativeagents conformance examples/sample-plugin
bash examples/sample-plugin/smoke.sh
```

---

## Cross-cutting quality gates

These apply **continuously**, not just at M10. Any PR that regresses one of these is not mergeable.

- [ ] **Test coverage ≥ 90% lines, ≥ 85% branches** across `src/nativeagents_sdk/`. Enforced in CI via `coverage report --fail-under`.
- [ ] **`ruff check .` zero findings.** No `# noqa` without a referenced ticket comment.
- [ ] **`ruff format --check .` clean.**
- [ ] **`mypy --strict src/nativeagents_sdk` zero errors.** No `# type: ignore` without a referenced ticket.
- [ ] **`pytest -q` passes** on every push and PR, on the matrix `{python: [3.11, 3.12]} × {os: [ubuntu-latest, macos-latest]}`.
- [ ] **No test takes longer than 10 seconds** unless explicitly marked `@pytest.mark.slow`. Slow tests run nightly, not on every PR.
- [ ] **No network access in tests.** Enforced via `pytest-socket` disallowing by default.
- [ ] **No writes outside `tmp_path`** in any unit test. Enforced via a `conftest.py` fixture that monkeypatches `NATIVEAGENTS_HOME` to `tmp_path`.
- [ ] **Deterministic builds.** `pip install -e .` with the same lockfile + Python version produces the same installed package. `hash` of the built wheel is stable across two CI runs on the same commit.
- [ ] **No circular imports.** Enforced by an `importtime` test that imports every submodule in isolation.
- [ ] **Public API guard.** `nativeagents_sdk.__all__` is exhaustive and tested. A test diff-checks `dir(nativeagents_sdk)` against `__all__` to catch accidental exports.
- [ ] **Docstring coverage.** Every public class and function has a docstring. Enforced by `interrogate` (or equivalent) at ≥ 95%.
- [ ] **Security.** `pip-audit` (or `safety check`) runs in CI and fails on HIGH/CRITICAL advisories in direct deps.
- [ ] **No `print()` in `src/`.** Everything goes through `logging`. Enforced by ruff rule `T20`.
- [ ] **No TODOs without a ticket reference.** `ruff` rule `FIX002` or custom grep in CI.

---

## End-to-end acceptance tests

These are the scenarios that prove we've built the right thing, not just that individual pieces work. They live in `tests/e2e/` and run in CI (not marked `slow`).

### E2E-1: Third-party "hello world" plugin in one file

> A third-party author writes a Python file, a `plugin.toml`, and runs `nativeagents install .`. It just works.

- [ ] Test creates `tmp_path/myplugin/plugin.toml` + `hooks.py` with a single `@dispatcher.on("PreToolUse")` handler that writes a custom audit event field.
- [ ] `nativeagents install tmp_path/myplugin` succeeds.
- [ ] Simulating a Claude Code `PreToolUse` invocation (writing JSON to the generated hook script via subprocess) produces exactly one audit row and one spool file.
- [ ] `nativeagents conformance tmp_path/myplugin` passes.
- [ ] `nativeagents uninstall myplugin` removes the hook and the plugin dir; audit rows remain.

### E2E-2: Three-plugin coexistence

> A user installs three plugins with overlapping events. Each plugin's handler runs, each writes to audit, none steps on the others.

- [ ] Fixture: `sample-plugin`, `noisy-plugin` (writes 10 events per hook), `quiet-plugin` (writes 1 event per hook). All three register `PreToolUse`.
- [ ] After 50 simulated `PreToolUse` events, audit has exactly 50 × 12 = 600 rows, evenly split by `plugin_name`.
- [ ] Each plugin's chain verifies independently.
- [ ] Global chain (ordered by `id`) verifies.
- [ ] `settings.json` contains three distinct hook entries, each with its own `nativeagents_plugin` marker.

### E2E-3: Uninstall & reinstall preserves user data

- [ ] Install reference plugin, generate 100 events.
- [ ] Uninstall; audit rows and memory entries remain; `plugins/<name>/` gone; `bin/<name>-*` gone; `settings.json` entry gone.
- [ ] Reinstall same plugin; existing events still visible via `AuditStore.iter_events`; new events append cleanly; chain verifies across the install boundary.

### E2E-4: Tamper detection on the audit chain

- [ ] Install plugin, generate 500 events.
- [ ] Directly mutate one row's `payload_json` in SQLite.
- [ ] `nativeagents doctor` reports exactly which `id` broke the chain and exits non-zero.

### E2E-5: Schema evolution forward-compat

- [ ] Open an SDK-0.1.0 DB with a hypothetical SDK-0.2.0 that bumps `SCHEMA_VERSION` by 1 and adds a migration.
- [ ] Migration runs once, idempotent on re-open, chain still verifies.
- [ ] Old plugin (SDK-0.1.0 as a dep) opening the new DB raises `SchemaVersionMismatch` with an actionable error message.

### E2E-6: Crash resilience

- [ ] Spawn a dispatcher subprocess, kill -9 it mid-write.
- [ ] Restart a new dispatcher. No stale `tmp/` files after `SpoolWriter.startup_cleanup()`. No half-committed rows. Chain verifies.

### E2E-7: Conformance harness catches real bugs

- [ ] For each failure mode in `tests/fixtures/broken_plugin/`, the harness emits exactly one failed check with a message that names the violated contract section.

---

## Documentation acceptance

A new engineer, given only the repo and one hour, must be able to:

- [ ] Read `README.md` and understand what the SDK is and what it is not.
- [ ] Read `contract/plugin-manifest.md` + `contract/hooks.md` and write a no-op `PreToolUse` plugin without reading the SDK source.
- [ ] Run `nativeagents conformance <their-plugin>` and interpret the output.
- [ ] Explain the hash chain to a colleague using only `contract/audit.md`.

Verification: during a PR review of v0.1.0, at least one engineer who did **not** write the SDK performs this walk-through and signs off in the PR.

---

## Release readiness checklist (v0.1.0)

All of the following must be green in the `v0.1.0` release PR:

- [ ] All M0–M10 must-pass items ticked.
- [ ] All cross-cutting quality gates green on `main`.
- [ ] All E2E acceptance tests pass in CI.
- [ ] `contract/` is complete and reviewed.
- [ ] `README.md` install command works from a fresh environment.
- [ ] `CHANGELOG.md` v0.1.0 entry written.
- [ ] `pyproject.toml` metadata complete; `twine check` clean.
- [ ] TestPyPI dry-run successful.
- [ ] At least one downstream repo (agentaudit-cc, agentmemory-cc, or agentwiki-cc) has a *draft* PR migrating onto the SDK, proving the contract fits real plugins. (It does not need to merge to release v0.1.0; it must exist.)
- [ ] The reference plugin runs against a live Claude Code session on the author's machine; screenshot/transcript attached to the release notes.
- [ ] `v0.1.0` git tag applied on the commit where this file last updated.

---

## Explicit non-goals for v0.1.0 (do not let scope creep re-open these)

- Wiki-related SDK APIs beyond path ownership. The agentwiki plugin owns its own derivation logic; the SDK only provides the `wiki/` directory namespace.
- Policy enforcement runtime. The SDK emits and stores audit events; policy evaluation lives in the agentaudit plugin, not in the SDK.
- Sidecar logic. Anything that ships data off the machine is the sidecar's concern, not the SDK's.
- Windows support beyond "paths don't hardcode POSIX." Full Windows testing is deferred to v0.2.
- IDE integrations beyond Claude Code. Copilot/others are v0.3+.
- Network transport. The SDK writes locally; uploads are the sidecar's job.
- Encryption at rest. Deferred — documented as a known gap in `contract/audit.md`.

If you find yourself wanting to do any of the above to close a milestone, **stop and escalate**. The boundary between SDK and plugins is the product.

---

## Sign-off

This document is considered satisfied when:

1. Every checkbox above is ticked.
2. Two reviewers (including one who did not write the SDK) sign off on the release PR.
3. `v0.1.0` is tagged, published to PyPI, and the reference plugin installs cleanly from the published wheel in a fresh environment.

At that point, handoff to Phase 2 (downstream plugin migrations and the super-repo) begins.
