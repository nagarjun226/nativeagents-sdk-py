"""Tests for nativeagents-sdk validate-plugin CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

from nativeagents_sdk.cli.main import app

runner = CliRunner()


def create_valid_plugin(tmp_path: Path, name: str = "test-plugin") -> Path:
    """Create a minimal valid plugin directory for testing."""
    plugin_dir = tmp_path / name
    hooks_dir = plugin_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    (plugin_dir / "plugin.toml").write_text(
        f"""schema_version = 1

[plugin]
name = "{name}"
version = "0.1.0"
description = "A test plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = ["plugins/{name}/"]
hook_module = "{name.replace("-", "_")}.hook"
min_sdk_version = "0.1.0"
""",
        encoding="utf-8",
    )
    (hooks_dir / "hook.sh").write_text("#!/bin/bash\necho 'hook'\n", encoding="utf-8")
    return plugin_dir


def test_validate_valid_plugin(tmp_path, isolated_home):
    """validate-plugin passes for a valid plugin."""
    plugin_dir = create_valid_plugin(tmp_path)
    result = runner.invoke(app, ["validate-plugin", str(plugin_dir)])
    assert result.exit_code == 0, result.output


def test_validate_missing_plugin_toml(tmp_path, isolated_home):
    """validate-plugin fails when plugin.toml is missing."""
    empty_dir = tmp_path / "empty-plugin"
    empty_dir.mkdir()
    result = runner.invoke(app, ["validate-plugin", str(empty_dir)])
    assert result.exit_code != 0


def test_validate_nonexistent_path(isolated_home):
    """validate-plugin fails for non-existent path."""
    result = runner.invoke(app, ["validate-plugin", "/nonexistent/path"])
    assert result.exit_code != 0


def test_validate_json_output(tmp_path, isolated_home):
    """validate-plugin --json outputs valid JSON."""
    import json

    plugin_dir = create_valid_plugin(tmp_path)
    result = runner.invoke(app, ["validate-plugin", str(plugin_dir), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "passed" in data
    assert "checks" in data
