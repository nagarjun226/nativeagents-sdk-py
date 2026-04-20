"""Tests for install.doctor module."""

from __future__ import annotations

import json
from pathlib import Path

from nativeagents_sdk.install.doctor import DoctorReport, doctor


def _write_minimal_plugin_toml(p_dir: Path) -> None:
    """Write a valid plugin.toml into a plugin directory."""
    (p_dir / "plugin.toml").write_text(
        """schema_version = 1

[plugin]
name = "test-plugin"
version = "0.1.0"
description = "A test plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = ["plugins/test-plugin/"]
hook_module = "test_plugin.hook"
min_sdk_version = "0.1.0"
""",
        encoding="utf-8",
    )


def _register_plugin_in_settings(claude_home: Path, plugin_name: str, hook_script: str) -> None:
    """Write settings.json with a registered plugin."""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_script,
                            "nativeagents_plugin": plugin_name,
                        }
                    ],
                }
            ]
        }
    }
    settings_path = claude_home / "settings.json"
    settings_path.write_text(json.dumps(settings), encoding="utf-8")


def test_doctor_all_passing(isolated_home: tuple[Path, Path]) -> None:
    """doctor() returns a healthy report when everything is in order."""
    na_home, claude_home = isolated_home

    # Set up the plugin directory
    p_dir = na_home / "plugins" / "test-plugin"
    p_dir.mkdir(parents=True)
    logs_dir = p_dir / "logs"
    logs_dir.mkdir()
    _write_minimal_plugin_toml(p_dir)
    _register_plugin_in_settings(claude_home, "test-plugin", "/fake/hook.sh")

    report = doctor("test-plugin")

    assert report.plugin_name == "test-plugin"
    assert report.is_healthy
    assert len(report.checks) > 0
    assert all(c["passed"] for c in report.checks)


def test_doctor_missing_plugin_dir(isolated_home: tuple[Path, Path]) -> None:
    """doctor() reports failure when plugin directory doesn't exist."""
    na_home, _claude_home = isolated_home
    # Don't create the plugin directory at all
    assert not (na_home / "plugins" / "test-plugin").exists()

    report = doctor("test-plugin")

    assert not report.is_healthy
    state_check = next((c for c in report.checks if c["name"] == "state_dir"), None)
    assert state_check is not None
    assert not state_check["passed"]


def test_doctor_missing_plugin_toml(isolated_home: tuple[Path, Path]) -> None:
    """doctor() reports failure when plugin.toml is missing."""
    na_home, _claude_home = isolated_home

    p_dir = na_home / "plugins" / "test-plugin"
    p_dir.mkdir(parents=True)
    logs_dir = p_dir / "logs"
    logs_dir.mkdir()
    # Deliberately NOT writing plugin.toml

    report = doctor("test-plugin")

    toml_check = next((c for c in report.checks if c["name"] == "plugin.toml"), None)
    assert toml_check is not None
    assert not toml_check["passed"]


def test_doctor_not_registered(isolated_home: tuple[Path, Path]) -> None:
    """doctor() reports failure when plugin is not registered."""
    na_home, _claude_home = isolated_home

    p_dir = na_home / "plugins" / "test-plugin"
    p_dir.mkdir(parents=True)
    logs_dir = p_dir / "logs"
    logs_dir.mkdir()
    _write_minimal_plugin_toml(p_dir)
    # Deliberately NOT registering in settings.json

    report = doctor("test-plugin")

    reg_check = next((c for c in report.checks if c["name"] == "registered"), None)
    assert reg_check is not None
    assert not reg_check["passed"]


def test_doctor_report_to_text() -> None:
    """DoctorReport.to_text() produces a human-readable string."""
    report = DoctorReport(
        plugin_name="my-plugin",
        checks=[
            {"name": "plugin.toml", "passed": True, "message": "Valid"},
            {"name": "state_dir", "passed": False, "message": "Not found"},
        ],
    )
    text = report.to_text()
    assert "my-plugin" in text
    assert "PASS" in text
    assert "FAIL" in text
    assert "unhealthy" in text


def test_doctor_report_is_healthy_empty() -> None:
    """is_healthy returns True when there are no checks (vacuously true)."""
    report = DoctorReport(plugin_name="test", checks=[])
    assert report.is_healthy


def test_doctor_invalid_plugin_toml(isolated_home: tuple[Path, Path]) -> None:
    """doctor() reports failure when plugin.toml is malformed."""
    na_home, _claude_home = isolated_home

    p_dir = na_home / "plugins" / "test-plugin"
    p_dir.mkdir(parents=True)
    logs_dir = p_dir / "logs"
    logs_dir.mkdir()
    # Write invalid TOML
    (p_dir / "plugin.toml").write_text("this is not valid toml ][", encoding="utf-8")

    report = doctor("test-plugin")

    toml_check = next((c for c in report.checks if c["name"] == "plugin.toml"), None)
    assert toml_check is not None
    assert not toml_check["passed"]
