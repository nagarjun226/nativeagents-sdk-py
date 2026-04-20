"""Tests for the check-contract CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from nativeagents_sdk.cli.main import app

runner = CliRunner()


def _setup_valid_plugin(na_home: Path, claude_home: Path, plugin_name: str) -> None:
    """Set up a valid plugin installation."""
    p_dir = na_home / "plugins" / plugin_name
    p_dir.mkdir(parents=True)
    logs_dir = p_dir / "logs"
    logs_dir.mkdir()

    (p_dir / "plugin.toml").write_text(
        f"""schema_version = 1

[plugin]
name = "{plugin_name}"
version = "0.1.0"
description = "A test plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = ["plugins/{plugin_name}/"]
hook_module = "test_plugin.hook"
min_sdk_version = "0.1.0"
""",
        encoding="utf-8",
    )

    # Register in settings.json
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/fake/hook.sh",
                            "nativeagents_plugin": plugin_name,
                        }
                    ],
                }
            ]
        }
    }
    (claude_home / "settings.json").write_text(json.dumps(settings), encoding="utf-8")


def test_check_contract_no_plugins(isolated_home: tuple[Path, Path]) -> None:
    """check-contract with no plugins prints a message and exits 0."""
    result = runner.invoke(app, ["check-contract"])
    assert result.exit_code == 0
    assert "No plugins" in result.output


def test_check_contract_healthy_plugin(isolated_home: tuple[Path, Path]) -> None:
    """check-contract with a healthy plugin exits 0."""
    na_home, claude_home = isolated_home
    _setup_valid_plugin(na_home, claude_home, "test-plugin")

    result = runner.invoke(app, ["check-contract"])
    assert result.exit_code == 0


def test_check_contract_json_output(isolated_home: tuple[Path, Path]) -> None:
    """check-contract --json produces JSON-parseable output."""
    na_home, claude_home = isolated_home
    _setup_valid_plugin(na_home, claude_home, "test-plugin")

    result = runner.invoke(app, ["check-contract", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["plugin_name"] == "test-plugin"


def test_check_contract_unhealthy_plugin_exits_1(isolated_home: tuple[Path, Path]) -> None:
    """check-contract with an unhealthy plugin exits 1."""
    na_home, claude_home = isolated_home

    # Create plugin with a valid plugin.toml so it's discoverable
    p_dir = na_home / "plugins" / "broken-plugin"
    p_dir.mkdir(parents=True)
    (p_dir / "logs").mkdir()
    # Write plugin.toml so discover_plugins() finds it
    (p_dir / "plugin.toml").write_text(
        """schema_version = 1

[plugin]
name = "broken-plugin"
version = "0.1.0"
description = "Broken test plugin"
hooks = ["PreToolUse"]
""",
        encoding="utf-8",
    )
    # But do NOT register it in settings.json → doctor will report FAIL

    result = runner.invoke(app, ["check-contract"])
    assert result.exit_code == 1
