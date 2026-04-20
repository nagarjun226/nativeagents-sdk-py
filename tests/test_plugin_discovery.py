"""Tests for plugin discovery."""

from __future__ import annotations

import pytest

from nativeagents_sdk.errors import DuplicatePluginError
from nativeagents_sdk.plugin.discovery import discover_plugins, resolve_plugin
from nativeagents_sdk.plugin.manifest import save_plugin_manifest
from nativeagents_sdk.schema.plugin import PluginManifest


def make_manifest(name: str) -> PluginManifest:
    return PluginManifest(
        schema_version=1,
        name=name,
        version="0.1.0",
        description=f"Plugin {name}",
        hooks=["PreToolUse"],
        writes_audit_events=False,
        owns_paths=[f"plugins/{name}/"],
    )


def install_plugin(name: str, isolated_home) -> None:
    """Install a plugin manifest into the test home."""
    from nativeagents_sdk.paths import ensure_dir, plugin_dir

    p_dir = plugin_dir(name)
    ensure_dir(p_dir)
    save_plugin_manifest(p_dir / "plugin.toml", make_manifest(name))


def test_discover_empty(isolated_home):
    """discover_plugins() returns [] when no plugins installed."""
    assert discover_plugins() == []


def test_discover_one_plugin(isolated_home):
    """discover_plugins() finds one installed plugin."""
    install_plugin("my-plugin", isolated_home)
    plugins = discover_plugins()
    assert len(plugins) == 1
    assert plugins[0].name == "my-plugin"


def test_discover_multiple_plugins(isolated_home):
    """discover_plugins() finds multiple installed plugins."""
    for name in ["plugin-a", "plugin-b", "plugin-c"]:
        install_plugin(name, isolated_home)
    plugins = discover_plugins()
    names = {p.name for p in plugins}
    assert names == {"plugin-a", "plugin-b", "plugin-c"}


def test_discover_skips_malformed(isolated_home):
    """discover_plugins() skips malformed plugin.toml files."""
    from nativeagents_sdk.paths import ensure_dir, plugin_dir

    # Valid plugin
    install_plugin("valid-plugin", isolated_home)

    # Malformed plugin
    bad_dir = plugin_dir("bad-plugin")
    ensure_dir(bad_dir)
    (bad_dir / "plugin.toml").write_text("{invalid toml\n", encoding="utf-8")

    plugins = discover_plugins()
    names = {p.name for p in plugins}
    assert "valid-plugin" in names
    assert "bad-plugin" not in names


def test_discover_duplicate_raises(isolated_home):
    """discover_plugins() raises DuplicatePluginError for duplicate names."""
    from nativeagents_sdk.paths import ensure_dir, memory_dir

    # Install in plugins/
    install_plugin("my-plugin", isolated_home)

    # Also install as memory plugin with same name
    mem_dir = memory_dir()
    ensure_dir(mem_dir)
    # Create a manifest with same name in memory dir
    manifest = PluginManifest(
        schema_version=1,
        name="my-plugin",  # Duplicate!
        version="0.2.0",
        description="Duplicate",
        well_known_namespace="memory",
        owns_paths=[],
        hooks=[],
        writes_audit_events=False,
    )
    save_plugin_manifest(mem_dir / "plugin.toml", manifest)

    with pytest.raises(DuplicatePluginError):
        discover_plugins()


def test_resolve_existing_plugin(isolated_home):
    """resolve_plugin() finds an installed plugin by name."""
    install_plugin("my-plugin", isolated_home)
    manifest = resolve_plugin("my-plugin")
    assert manifest is not None
    assert manifest.name == "my-plugin"


def test_resolve_nonexistent_returns_none(isolated_home):
    """resolve_plugin() returns None for non-existent plugin."""
    result = resolve_plugin("nonexistent")
    assert result is None
