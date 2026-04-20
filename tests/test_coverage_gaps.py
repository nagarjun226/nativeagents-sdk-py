"""Targeted tests to fill coverage gaps across multiple modules.

These complement the per-module test files and cover specific uncovered branches.
"""

from __future__ import annotations

import io
import json
import sqlite3
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# audit/migrations.py — lines 40, 44-45, 73-82, 91-93
# ---------------------------------------------------------------------------


def test_migrate_from_version_0(isolated_home: tuple[Path, Path]) -> None:
    """migrate() from version 0 runs _migrate_0_to_1 and updates schema_version."""
    from nativeagents_sdk.audit.migrations import CURRENT_SCHEMA_VERSION, migrate

    na_home, _ = isolated_home
    db_path = na_home / "test_migrate.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create meta table with version 0
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES ('schema_version', '0')")
    conn.commit()

    migrate(conn, target_version=CURRENT_SCHEMA_VERSION, from_version=0)

    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert int(row["value"]) == CURRENT_SCHEMA_VERSION
    conn.close()


def test_migrate_no_meta_row_defaults_to_zero(isolated_home: tuple[Path, Path]) -> None:
    """migrate() with no schema_version row in meta defaults from_version to 0."""
    from nativeagents_sdk.audit.migrations import migrate

    na_home, _ = isolated_home
    db_path = na_home / "test_no_meta.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create meta table with no schema_version row
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.commit()

    # Should not raise — defaults from_version=0
    migrate(conn, target_version=1, from_version=None)

    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert row is not None
    conn.close()


def test_ensure_schema_bad_schema_version_in_meta(isolated_home: tuple[Path, Path]) -> None:
    """ensure_schema() handles a non-numeric schema_version gracefully."""
    from nativeagents_sdk.audit.migrations import ensure_schema

    na_home, _ = isolated_home
    db_path = na_home / "test_bad_version.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Set up a meta table with a non-integer version
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES ('schema_version', 'not-a-number')")
    conn.commit()

    # Should handle gracefully by falling back to version 0
    ensure_schema(conn)
    conn.close()


# ---------------------------------------------------------------------------
# memory/manifest.py — validate_file, OSError paths, not-a-dict
# ---------------------------------------------------------------------------


def test_validate_file_valid(tmp_path: Path) -> None:
    """validate_file() returns empty list for a valid memory file."""
    from nativeagents_sdk.memory.manifest import validate_file

    f = tmp_path / "valid.md"
    f.write_text(
        "---\nname: Test\ntoken_budget: 100\n---\nbody\n",
        encoding="utf-8",
    )
    errors = validate_file(f)
    assert errors == []


def test_validate_file_missing(tmp_path: Path) -> None:
    """validate_file() returns empty list for a missing file (no crash)."""
    from nativeagents_sdk.memory.manifest import validate_file

    errors = validate_file(tmp_path / "nonexistent.md")
    assert errors == []


def test_validate_file_no_frontmatter(tmp_path: Path) -> None:
    """validate_file() handles a file with no YAML frontmatter."""
    from nativeagents_sdk.memory.manifest import validate_file

    f = tmp_path / "no_fm.md"
    f.write_text("# No frontmatter\n\nJust body text.\n", encoding="utf-8")
    errors = validate_file(f)
    # Should not crash; FrontmatterError is caught internally
    assert isinstance(errors, list)


def test_load_manifest_not_a_dict(tmp_path: Path) -> None:
    """load_manifest() raises ManifestError when root is not a JSON object."""
    from nativeagents_sdk.errors import ManifestError
    from nativeagents_sdk.memory.manifest import load_manifest

    p = tmp_path / "manifest.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON object"):
        load_manifest(p)


def test_rebuild_manifest_nonexistent_dir(isolated_home: tuple[Path, Path]) -> None:
    """rebuild_manifest() on a non-existent directory returns empty Manifest."""
    from nativeagents_sdk.memory.manifest import rebuild_manifest

    na_home, _ = isolated_home
    fake_dir = na_home / "does-not-exist"
    manifest = rebuild_manifest(fake_dir)
    assert manifest.files == []


def test_rebuild_manifest_skips_oserror(tmp_path: Path) -> None:
    """rebuild_manifest() logs and skips files it cannot read."""
    from nativeagents_sdk.memory.manifest import rebuild_manifest

    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()

    # Write a valid file
    (mem_dir / "good.md").write_text(
        "---\nname: Good\ntoken_budget: 50\n---\nbody\n",
        encoding="utf-8",
    )

    # Write a valid-looking file then chmod it unreadable (Unix only)
    bad = mem_dir / "bad.md"
    bad.write_text("---\nname: Bad\ntoken_budget: 50\n---\nbody\n", encoding="utf-8")
    bad.chmod(0o000)

    try:
        manifest = rebuild_manifest(mem_dir)
        # Should get only the readable file
        assert len(manifest.files) == 1
        assert manifest.files[0].name == "Good"
    finally:
        bad.chmod(0o644)  # restore so tmp_path can be cleaned up


# ---------------------------------------------------------------------------
# hooks/runtime.py — non-dict JSON, no event name, validation fallback
# ---------------------------------------------------------------------------


def test_read_hook_input_non_dict_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """read_hook_input() exits 1 if stdin is JSON but not an object."""
    from nativeagents_sdk.hooks.runtime import read_hook_input

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps([1, 2, 3])))
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        read_hook_input()
    assert exc_info.value.code == 1


def test_read_hook_input_no_event_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """read_hook_input() exits 1 when neither HOOK_EVENT_NAME env nor payload field exists."""
    from nativeagents_sdk.hooks.runtime import read_hook_input

    payload = {"session_id": "abc", "cwd": "/tmp"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        read_hook_input()
    assert exc_info.value.code == 1


def test_read_hook_input_validation_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown event type falls back to base HookInput without crashing."""
    from nativeagents_sdk.hooks.runtime import read_hook_input
    from nativeagents_sdk.schema.events import HookInput

    # Unknown event type — HOOK_INPUT_MODELS will not have it, uses HookInput base
    payload = {
        "hook_event_name": "SomeFutureEvent",
        "session_id": "abc",
        "cwd": "/tmp",
        "permission_mode": "allow",
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    result = read_hook_input()
    assert isinstance(result, HookInput)


# ---------------------------------------------------------------------------
# hooks/dispatcher.py — write_audit, close, _build_context config failure
# ---------------------------------------------------------------------------


def test_hook_context_write_audit(isolated_home: tuple[Path, Path]) -> None:
    """HookContext.write_audit() writes an event to the audit DB."""
    from nativeagents_sdk.hooks.dispatcher import HookContext

    na_home, _ = isolated_home
    import logging

    from nativeagents_sdk.config import Config
    from nativeagents_sdk.paths import audit_db_path, ensure_dir, plugin_dir

    plugin_name = "test-plugin"
    p_dir = plugin_dir(plugin_name)
    logs_dir = p_dir / "logs"
    ensure_dir(logs_dir)

    ctx = HookContext(
        plugin_name=plugin_name,
        plugin_dir=p_dir,
        audit_db=audit_db_path(),
        config=Config(),
        log=logging.getLogger("test"),
    )

    row_hash = ctx.write_audit(
        event_type="test.event",
        payload={"x": 1},
        session_id="test-session-123",
    )

    assert isinstance(row_hash, str)
    assert len(row_hash) == 64  # SHA-256 hex
    ctx.close()


def test_hook_context_close_idempotent(isolated_home: tuple[Path, Path]) -> None:
    """HookContext.close() can be called multiple times without error."""
    import logging

    from nativeagents_sdk.config import Config
    from nativeagents_sdk.hooks.dispatcher import HookContext
    from nativeagents_sdk.paths import audit_db_path, ensure_dir, plugin_dir

    plugin_name = "test-plugin"
    p_dir = plugin_dir(plugin_name)
    logs_dir = p_dir / "logs"
    ensure_dir(logs_dir)

    ctx = HookContext(
        plugin_name=plugin_name,
        plugin_dir=p_dir,
        audit_db=audit_db_path(),
        config=Config(),
        log=logging.getLogger("test"),
    )

    ctx.close()
    ctx.close()  # Should not raise


def test_dispatcher_unknown_event_exits_0(
    monkeypatch: pytest.MonkeyPatch, isolated_home: tuple[Path, Path]
) -> None:
    """Dispatcher exits 0 when it receives an unknown event type."""
    from nativeagents_sdk.hooks.dispatcher import HookDispatcher

    dispatcher = HookDispatcher(plugin_name="test-plugin")

    payload = {
        "hook_event_name": "UnknownFutureEvent",
        "session_id": "abc123",
        "cwd": "/tmp",
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setenv("HOOK_EVENT_NAME", "UnknownFutureEvent")

    with pytest.raises(SystemExit) as exc_info:
        dispatcher.run()
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# plugin/manifest.py — save + edge cases
# ---------------------------------------------------------------------------


def test_save_and_load_plugin_manifest(tmp_path: Path) -> None:
    """save_plugin_manifest() + load_plugin_manifest() round-trips."""
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest, save_plugin_manifest
    from nativeagents_sdk.schema.plugin import PluginManifest

    manifest = PluginManifest(
        name="my-plugin",
        version="1.2.3",
        description="A test plugin",
        hooks=["PreToolUse", "PostToolUse"],
        writes_audit_events=True,
        owns_paths=["plugins/my-plugin/"],
        hook_module="my_plugin.hook",
        min_sdk_version="0.1.0",
    )

    path = tmp_path / "plugin.toml"
    save_plugin_manifest(path, manifest)
    loaded = load_plugin_manifest(path)

    assert loaded.name == manifest.name
    assert loaded.version == manifest.version
    assert set(loaded.hooks) == set(manifest.hooks)
    assert loaded.writes_audit_events is True


def test_load_plugin_manifest_missing_file(tmp_path: Path) -> None:
    """load_plugin_manifest() raises PluginManifestError for missing file."""
    from nativeagents_sdk.errors import PluginManifestError
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest

    with pytest.raises(PluginManifestError, match="not found"):
        load_plugin_manifest(tmp_path / "nonexistent.toml")


# ---------------------------------------------------------------------------
# install/register.py — backup file creation, write_claude_settings
# ---------------------------------------------------------------------------


def test_register_creates_backup(isolated_home: tuple[Path, Path]) -> None:
    """register_plugin() creates a .bak file before modifying settings.json."""
    from nativeagents_sdk.install.register import register_plugin
    from nativeagents_sdk.schema.plugin import PluginManifest

    na_home, claude_home = isolated_home

    # Write an existing settings.json
    settings_path = claude_home / "settings.json"
    settings_path.write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    manifest = PluginManifest(
        name="backup-test-plugin",
        version="0.1.0",
        description="Test",
        hooks=["PreToolUse"],
    )
    hook_script = na_home / "hook.sh"
    hook_script.write_text("#!/bin/bash\nexit 0\n")

    register_plugin(manifest, hook_script)

    # A backup file should exist
    backups = list(claude_home.glob("settings.json.bak.*"))
    assert len(backups) >= 1


def test_unregister_no_op_when_not_registered(isolated_home: tuple[Path, Path]) -> None:
    """unregister_plugin() is a no-op when plugin is not registered."""
    from nativeagents_sdk.install.register import unregister_plugin

    # Should not raise even with no settings.json
    unregister_plugin("nonexistent-plugin")
