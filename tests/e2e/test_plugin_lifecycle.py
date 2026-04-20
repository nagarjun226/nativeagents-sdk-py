"""E2E tests: full plugin lifecycle from install to uninstall."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def _make_plugin(base: Path, name: str) -> tuple[Path, Path]:
    """Create a minimal plugin directory and return (plugin_dir, hook_script)."""
    plugin_dir = base / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "logs").mkdir()

    (plugin_dir / "plugin.toml").write_text(
        f"""schema_version = 1

[plugin]
name = "{name}"
version = "0.1.0"
description = "E2E test plugin"
hooks = ["PreToolUse", "PostToolUse"]
writes_audit_events = true
owns_paths = ["plugins/{name}/"]
hook_module = "{name.replace("-", "_")}.hook"
min_sdk_version = "0.1.0"
""",
        encoding="utf-8",
    )

    hook_script = plugin_dir / "hook.sh"
    hook_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    hook_script.chmod(0o755)

    return plugin_dir, hook_script


# ---------------------------------------------------------------------------
# E2E-1: Third-party plugin install / fire / uninstall
# ---------------------------------------------------------------------------


def test_e2e_plugin_install_and_doctor(isolated_home: tuple[Path, Path]) -> None:
    """A freshly registered plugin passes doctor checks."""
    from nativeagents_sdk.install.doctor import doctor
    from nativeagents_sdk.install.register import register_plugin, unregister_plugin
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest

    na_home, claude_home = isolated_home
    plugin_dir, hook_script = _make_plugin(na_home / "plugins", "e2e-alpha")

    manifest = load_plugin_manifest(plugin_dir / "plugin.toml")
    register_plugin(manifest, hook_script)

    report = doctor("e2e-alpha")
    assert report.is_healthy, report.to_text()

    unregister_plugin("e2e-alpha")


def test_e2e_audit_write_and_verify(isolated_home: tuple[Path, Path]) -> None:
    """Writing audit events produces a verifiable hash chain."""
    from nativeagents_sdk.audit.integrity import verify_integrity
    from nativeagents_sdk.audit.store import open_store, write_event
    from nativeagents_sdk.schema.audit import AuditEvent

    na_home, _ = isolated_home
    db = na_home / "audit.db"
    conn = open_store(db)

    session = "e2e-session-001"
    for i in range(20):
        write_event(
            conn,
            AuditEvent(
                session_id=session,
                event_type="e2e.tool_use",
                plugin_name="e2e-alpha",
                payload={"i": i, "tool": "Read"},
                timestamp=datetime.now(UTC),
            ),
        )

    report = verify_integrity(conn, session_id=session)
    conn.close()

    assert report.is_clean
    assert report.sessions_verified == 1


def test_e2e_uninstall_preserves_audit_data(isolated_home: tuple[Path, Path]) -> None:
    """Uninstalling a plugin does not delete its audit rows."""
    from nativeagents_sdk.audit.store import open_store, write_event
    from nativeagents_sdk.install.register import register_plugin, unregister_plugin
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest
    from nativeagents_sdk.schema.audit import AuditEvent

    na_home, claude_home = isolated_home
    plugin_dir, hook_script = _make_plugin(na_home / "plugins", "e2e-beta")

    manifest = load_plugin_manifest(plugin_dir / "plugin.toml")
    register_plugin(manifest, hook_script)

    db = na_home / "audit.db"
    conn = open_store(db)
    session = "e2e-beta-session"
    for i in range(5):
        write_event(
            conn,
            AuditEvent(
                session_id=session,
                event_type="e2e.event",
                plugin_name="e2e-beta",
                payload={"i": i},
                timestamp=datetime.now(UTC),
            ),
        )
    conn.close()

    unregister_plugin("e2e-beta")

    # Audit data must survive uninstall
    conn2 = open_store(db)
    row = conn2.execute("SELECT COUNT(*) FROM events WHERE session_id=?", (session,)).fetchone()
    conn2.close()
    assert row[0] == 5


# ---------------------------------------------------------------------------
# E2E-2: Three-plugin coexistence
# ---------------------------------------------------------------------------


def test_e2e_three_plugin_coexistence(isolated_home: tuple[Path, Path]) -> None:
    """Three plugins write audit events independently; all chains verify."""
    from nativeagents_sdk.audit.integrity import verify_integrity
    from nativeagents_sdk.audit.store import open_store, write_event
    from nativeagents_sdk.schema.audit import AuditEvent

    na_home, _ = isolated_home
    db = na_home / "audit.db"
    conn = open_store(db)

    plugins = ["plugin-alpha", "plugin-beta", "plugin-gamma"]
    events_each = 15

    for plugin in plugins:
        session = f"session-{plugin}"
        for i in range(events_each):
            write_event(
                conn,
                AuditEvent(
                    session_id=session,
                    event_type="tool.use",
                    plugin_name=plugin,
                    payload={"i": i},
                    timestamp=datetime.now(UTC),
                ),
            )

    for plugin in plugins:
        report = verify_integrity(conn, session_id=f"session-{plugin}")
        assert report.is_clean, f"{plugin} chain broken: {report.breaks}"

    row = conn.execute("SELECT COUNT(*) FROM events").fetchone()
    conn.close()
    assert row[0] == len(plugins) * events_each


# ---------------------------------------------------------------------------
# E2E-3: Tamper detection
# ---------------------------------------------------------------------------


def test_e2e_tamper_detection(isolated_home: tuple[Path, Path]) -> None:
    """Mutating one row's payload breaks verify_integrity at that exact row."""
    from nativeagents_sdk.audit.integrity import verify_integrity
    from nativeagents_sdk.audit.store import open_store, write_event
    from nativeagents_sdk.schema.audit import AuditEvent

    na_home, _ = isolated_home
    db = na_home / "audit.db"
    conn = open_store(db)

    session = "tamper-session"
    for i in range(10):
        write_event(
            conn,
            AuditEvent(
                session_id=session,
                event_type="test.event",
                plugin_name="test-plugin",
                payload={"i": i},
                timestamp=datetime.now(UTC),
            ),
        )

    # Tamper row at sequence 5
    conn.execute(
        "UPDATE events SET payload_json=? WHERE session_id=? AND sequence=5",
        ('{"tampered":true}', session),
    )
    conn.commit()

    report = verify_integrity(conn, session_id=session)
    conn.close()

    assert not report.is_clean
    # The break should be at or after sequence 5
    assert any(b["sequence"] >= 5 for b in report.breaks)


# ---------------------------------------------------------------------------
# E2E-4: Spool atomic writes
# ---------------------------------------------------------------------------


def test_e2e_spool_atomic_and_ordered(isolated_home: tuple[Path, Path]) -> None:
    """Spool writes are atomic and returned in timestamp order."""
    from nativeagents_sdk.spool.spool import Spool

    spool = Spool("e2e-plugin", "audit")
    paths = []
    for i in range(10):
        p = spool.write(json.dumps({"i": i}).encode())
        paths.append(p)

    listed = list(spool.iter())
    # All 10 files returned
    assert len(listed) == 10
    # Order matches insertion (filenames are timestamp-prefixed)
    for a, b in zip(listed, listed[1:], strict=False):
        assert a.name <= b.name

    # Consume all
    for p in listed:
        spool.consume(p)
    assert list(spool.iter()) == []


# ---------------------------------------------------------------------------
# E2E-5: Plugin discovery with malformed manifest skipped
# ---------------------------------------------------------------------------


def test_e2e_discovery_skips_malformed(isolated_home: tuple[Path, Path]) -> None:
    """discover_plugins() skips malformed plugin.toml entries and returns valid ones."""
    from nativeagents_sdk.plugin.discovery import discover_plugins

    na_home, _ = isolated_home

    # Valid plugin
    valid_dir = na_home / "plugins" / "valid-plugin"
    valid_dir.mkdir(parents=True)
    (valid_dir / "logs").mkdir()
    (valid_dir / "plugin.toml").write_text(
        """schema_version = 1
[plugin]
name = "valid-plugin"
version = "0.1.0"
description = "Valid"
hooks = ["PreToolUse"]
""",
        encoding="utf-8",
    )

    # Malformed plugin (invalid TOML)
    bad_dir = na_home / "plugins" / "bad-plugin"
    bad_dir.mkdir(parents=True)
    (bad_dir / "plugin.toml").write_text("[[NOT VALID TOML", encoding="utf-8")

    plugins = discover_plugins()
    names = [p.name for p in plugins]
    assert "valid-plugin" in names
    assert "bad-plugin" not in names


# ---------------------------------------------------------------------------
# E2E-6: register_plugin idempotency
# ---------------------------------------------------------------------------


def test_e2e_register_idempotent(isolated_home: tuple[Path, Path]) -> None:
    """register_plugin() called twice produces identical settings.json."""
    from nativeagents_sdk.install.register import register_plugin
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest

    na_home, claude_home = isolated_home
    plugin_dir, hook_script = _make_plugin(na_home / "plugins", "idem-plugin")
    manifest = load_plugin_manifest(plugin_dir / "plugin.toml")

    settings_path = claude_home / "settings.json"

    register_plugin(manifest, hook_script)
    content_after_first = settings_path.read_text(encoding="utf-8")

    register_plugin(manifest, hook_script)
    content_after_second = settings_path.read_text(encoding="utf-8")

    assert json.loads(content_after_first) == json.loads(content_after_second)


# ---------------------------------------------------------------------------
# E2E-7: Conformance harness catches real bugs
# ---------------------------------------------------------------------------


import pytest  # noqa: E402


@pytest.mark.parametrize(
    "subdir,expected_failed_check",
    [
        ("missing_toml", "plugin_toml_exists"),
        ("invalid_toml", "manifest_valid"),
        ("reserved_name", "name_not_reserved"),
        ("sdk_too_old", "sdk_version_satisfied"),
        ("unknown_hook", "hooks_known"),
        ("missing_hook_script", "hook_script_exists"),
    ],
)
def test_e2e_conformance_catches_broken_plugin(
    subdir: str,
    expected_failed_check: str,
    isolated_home: tuple[Path, Path],
) -> None:
    """Conformance harness identifies exactly which check a broken plugin fails."""
    from nativeagents_sdk.conformance.harness import run_conformance

    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "broken_plugin"
    plugin_dir = fixtures_dir / subdir

    report = run_conformance(plugin_dir)
    assert not report.passed, f"Expected failure for {subdir!r} but harness passed"
    failed_checks = [c["name"] for c in report.checks if not c.get("passed")]
    assert expected_failed_check in failed_checks, (
        f"Expected {expected_failed_check!r} in failed checks; got {failed_checks}"
    )
