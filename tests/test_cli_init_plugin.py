"""Tests for nativeagents-sdk init-plugin CLI command."""

from __future__ import annotations

from typer.testing import CliRunner

from nativeagents_sdk.cli.main import app

runner = CliRunner()


def test_init_plugin_creates_scaffold(tmp_path, isolated_home):
    """init-plugin creates the expected file structure."""
    result = runner.invoke(app, ["init-plugin", "my-plugin", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output

    plugin_dir = tmp_path / "my-plugin"
    assert plugin_dir.exists()
    assert (plugin_dir / "plugin.toml").exists()
    assert (plugin_dir / "pyproject.toml").exists()
    assert (plugin_dir / "src" / "my_plugin" / "__init__.py").exists()
    assert (plugin_dir / "src" / "my_plugin" / "hook.py").exists()
    assert (plugin_dir / "src" / "my_plugin" / "cli.py").exists()
    assert (plugin_dir / "hooks" / "hook.sh").exists()
    assert (plugin_dir / "tests" / "test_smoke.py").exists()


def test_init_plugin_toml_valid(tmp_path, isolated_home):
    """The generated plugin.toml is loadable."""
    runner.invoke(app, ["init-plugin", "test-plugin", "--output-dir", str(tmp_path)])
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest

    manifest = load_plugin_manifest(tmp_path / "test-plugin" / "plugin.toml")
    assert manifest.name == "test-plugin"
    assert manifest.version == "0.1.0"


def test_init_plugin_invalid_name(tmp_path, isolated_home):
    """init-plugin with invalid name exits non-zero."""
    result = runner.invoke(app, ["init-plugin", "Invalid_Name", "--output-dir", str(tmp_path)])
    assert result.exit_code != 0


def test_init_plugin_existing_dir_fails(tmp_path, isolated_home):
    """init-plugin fails if directory already exists."""
    existing = tmp_path / "my-plugin"
    existing.mkdir()
    result = runner.invoke(app, ["init-plugin", "my-plugin", "--output-dir", str(tmp_path)])
    assert result.exit_code != 0


def test_version_command(isolated_home):
    """version subcommand prints SDK version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "nativeagents-sdk" in result.output
    assert "0.2.0" in result.output


def test_hook_sh_is_executable(tmp_path, isolated_home):
    """Generated hook.sh has executable bit set."""
    runner.invoke(app, ["init-plugin", "exec-test", "--output-dir", str(tmp_path)])
    hook = tmp_path / "exec-test" / "hooks" / "hook.sh"
    assert hook.stat().st_mode & 0o111  # Any execute bit
