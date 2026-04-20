"""Tests for plugin manifest load/save."""

from __future__ import annotations

from pathlib import Path

import pytest

from nativeagents_sdk.errors import PluginManifestError
from nativeagents_sdk.plugin.manifest import load_plugin_manifest, save_plugin_manifest
from nativeagents_sdk.schema.plugin import PluginManifest

MINIMAL_TOML = """\
schema_version = 1

[plugin]
name = "hello-plugin"
version = "0.1.0"
description = "A minimal test plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = ["plugins/hello-plugin/"]
hook_module = "hello_plugin.hook"
min_sdk_version = "0.1.0"
"""


def test_load_minimal_manifest(tmp_path):
    """Load a minimal valid plugin.toml."""
    p = tmp_path / "plugin.toml"
    p.write_text(MINIMAL_TOML, encoding="utf-8")
    manifest = load_plugin_manifest(p)
    assert manifest.name == "hello-plugin"
    assert manifest.version == "0.1.0"
    assert "PreToolUse" in manifest.hooks


def test_load_missing_file(tmp_path):
    """load_plugin_manifest() raises PluginManifestError for missing file."""
    with pytest.raises(PluginManifestError):
        load_plugin_manifest(tmp_path / "nonexistent.toml")


def test_load_invalid_toml(tmp_path):
    """Invalid TOML raises PluginManifestError."""
    p = tmp_path / "plugin.toml"
    p.write_text("{not valid toml\n", encoding="utf-8")
    with pytest.raises(PluginManifestError, match="TOML"):
        load_plugin_manifest(p)


def test_load_invalid_plugin_name(tmp_path):
    """Invalid plugin name raises PluginManifestError."""
    p = tmp_path / "plugin.toml"
    p.write_text(
        'schema_version = 1\n[plugin]\nname = "Invalid_Name"\n'
        'version = "0.1.0"\ndescription = "test"\n',
        encoding="utf-8",
    )
    with pytest.raises(PluginManifestError):
        load_plugin_manifest(p)


def test_load_reserved_name(tmp_path):
    """Reserved plugin names raise PluginManifestError."""
    p = tmp_path / "plugin.toml"
    p.write_text(
        'schema_version = 1\n[plugin]\nname = "audit"\nversion = "0.1.0"\ndescription = "test"\n',
        encoding="utf-8",
    )
    with pytest.raises(PluginManifestError):
        load_plugin_manifest(p)


def test_load_invalid_hook_event(tmp_path):
    """Invalid hook event names raise PluginManifestError."""
    p = tmp_path / "plugin.toml"
    p.write_text(
        'schema_version = 1\n[plugin]\nname = "my-plugin"\n'
        'version = "0.1.0"\ndescription = "test"\nhooks = ["NotARealEvent"]\n',
        encoding="utf-8",
    )
    with pytest.raises(PluginManifestError):
        load_plugin_manifest(p)


def test_save_and_load_roundtrip(tmp_path):
    """save_plugin_manifest() + load_plugin_manifest() round-trips."""
    manifest = PluginManifest(
        schema_version=1,
        name="my-plugin",
        version="1.2.3",
        description="Test plugin",
        hooks=["PreToolUse", "Stop"],
        writes_audit_events=True,
        owns_paths=["plugins/my-plugin/"],
        hook_module="my_plugin.hook",
        cli_entry="my_plugin.cli:app",
        min_sdk_version="0.1.0",
    )
    p = tmp_path / "plugin.toml"
    save_plugin_manifest(p, manifest)
    loaded = load_plugin_manifest(p)

    assert loaded.name == manifest.name
    assert loaded.version == manifest.version
    assert sorted(loaded.hooks) == sorted(manifest.hooks)
    assert loaded.hook_module == manifest.hook_module


def test_load_with_requires(tmp_path):
    """plugin.toml with [plugin.requires] is parsed correctly."""
    p = tmp_path / "plugin.toml"
    p.write_text(
        """\
schema_version = 1

[plugin]
name = "my-plugin"
version = "0.1.0"
description = "test"

[plugin.requires]
optional = ["agentmemory"]
required = []
""",
        encoding="utf-8",
    )
    manifest = load_plugin_manifest(p)
    assert manifest.requires.optional == ["agentmemory"]


def test_load_schema_too_new(tmp_path):
    """schema_version > max raises PluginManifestError."""
    p = tmp_path / "plugin.toml"
    p.write_text(
        'schema_version = 999\n[plugin]\nname = "my-plugin"\n'
        'version = "0.1.0"\ndescription = "test"\n',
        encoding="utf-8",
    )
    with pytest.raises(PluginManifestError, match="schema_version"):
        load_plugin_manifest(p)


def test_load_from_fixtures_dir():
    """Load the test fixture plugin.toml."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    toml_path = fixtures_dir / "minimal_plugin.toml"
    if toml_path.exists():
        manifest = load_plugin_manifest(toml_path)
        assert manifest.name == "hello-plugin"


def test_invalid_semver_version(tmp_path):
    """Non-SemVer version string raises PluginManifestError."""
    p = tmp_path / "plugin.toml"
    p.write_text(
        'schema_version = 1\n[plugin]\nname = "my-plugin"\n'
        'version = "not-a-version"\ndescription = "test"\n',
        encoding="utf-8",
    )
    with pytest.raises(PluginManifestError):
        load_plugin_manifest(p)


def test_valid_semver_versions(tmp_path):
    """Valid SemVer versions are accepted."""
    for version in ["1.0.0", "0.1.0", "1.2.3-alpha.1", "2.0.0-rc1"]:
        p = tmp_path / "plugin.toml"
        p.write_text(
            f'schema_version = 1\n[plugin]\nname = "my-plugin"\n'
            f'version = "{version}"\ndescription = "test"\n',
            encoding="utf-8",
        )
        manifest = load_plugin_manifest(p)
        assert manifest.version == version


def test_reserved_prefix_name_rejected(tmp_path):
    """Plugin names with reserved prefixes raise PluginManifestError."""
    for name in ["native-logger", "sdk-helper", "system-core"]:
        p = tmp_path / "plugin.toml"
        p.write_text(
            f'schema_version = 1\n[plugin]\nname = "{name}"\n'
            'version = "0.1.0"\ndescription = "test"\n',
            encoding="utf-8",
        )
        with pytest.raises(PluginManifestError, match="reserved"):
            load_plugin_manifest(p)
