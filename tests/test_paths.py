"""Tests for nativeagents_sdk.paths module."""

from pathlib import Path

import pytest

from nativeagents_sdk.paths import (
    RESERVED_PLUGIN_NAMES,
    atomic_write,
    audit_db_path,
    bin_dir,
    claude_home,
    config_path,
    ensure_dir,
    ensure_layout,
    home,
    memory_dir,
    plugin_dir,
    policies_dir,
    spool_dir,
    validate_plugin_name,
    wiki_dir,
    wiki_inbox_dir,
)


def test_home_from_env(tmp_path, monkeypatch):
    """NATIVEAGENTS_HOME env var overrides default."""
    custom = tmp_path / "custom_home"
    monkeypatch.setenv("NATIVEAGENTS_HOME", str(custom))
    assert home() == custom


def test_home_default(tmp_path, monkeypatch):
    """Without env var, home() returns ~/.nativeagents."""
    monkeypatch.delenv("NATIVEAGENTS_HOME", raising=False)
    result = home()
    assert result == Path.home() / ".nativeagents"


def test_claude_home_from_env(tmp_path, monkeypatch):
    """CLAUDE_HOME env var overrides default."""
    custom = tmp_path / "custom_claude"
    monkeypatch.setenv("CLAUDE_HOME", str(custom))
    assert claude_home() == custom


def test_claude_home_default(monkeypatch):
    """Without env var, claude_home() returns ~/.claude."""
    monkeypatch.delenv("CLAUDE_HOME", raising=False)
    result = claude_home()
    assert result == Path.home() / ".claude"


def test_path_helpers_use_home(isolated_home):
    """All path helpers return paths under NATIVEAGENTS_HOME."""
    na_home, _ = isolated_home
    assert audit_db_path() == na_home / "audit.db"
    assert memory_dir() == na_home / "memory"
    assert wiki_dir() == na_home / "wiki"
    assert wiki_inbox_dir() == na_home / "wiki" / "raw-inbox"
    assert policies_dir() == na_home / "policies"
    assert spool_dir() == na_home / "spool"
    assert bin_dir() == na_home / "bin"
    assert config_path() == na_home / "config.yaml"


def test_plugin_dir(isolated_home):
    """plugin_dir() returns correct path."""
    na_home, _ = isolated_home
    assert plugin_dir("my-plugin") == na_home / "plugins" / "my-plugin"


def test_home_not_created_on_import(isolated_home, tmp_path):
    """Calling path functions does NOT create directories."""
    # isolated_home creates the dirs in conftest; we check a subdirectory
    subdir = home() / "plugins"
    assert not subdir.exists()


def test_ensure_dir_creates(isolated_home):
    """ensure_dir() creates the directory."""
    target = home() / "testdir" / "sub"
    assert not target.exists()
    ensure_dir(target)
    assert target.exists()
    assert target.is_dir()


def test_ensure_dir_idempotent(isolated_home):
    """ensure_dir() is safe to call multiple times."""
    target = home() / "testdir"
    ensure_dir(target)
    ensure_dir(target)  # Should not raise
    assert target.exists()


def test_atomic_write(isolated_home):
    """atomic_write() creates file with correct content."""
    target = home() / "test.txt"
    atomic_write(target, b"hello world")
    assert target.read_bytes() == b"hello world"


def test_atomic_write_overwrites(isolated_home):
    """atomic_write() overwrites existing file."""
    target = home() / "test.txt"
    atomic_write(target, b"original")
    atomic_write(target, b"updated")
    assert target.read_bytes() == b"updated"


def test_atomic_write_creates_parents(isolated_home):
    """atomic_write() creates parent directories if needed."""
    target = home() / "new" / "deep" / "file.txt"
    atomic_write(target, b"data")
    assert target.read_bytes() == b"data"


# --- Plugin name validation ---


def test_valid_plugin_names():
    """Valid plugin names pass validation."""
    valid_names = [
        "my-plugin",
        "agentaudit",
        "a",
        "plugin123",
        "x" * 40,
        "my-complex-plugin-name-123",
    ]
    for name in valid_names:
        assert validate_plugin_name(name) == name


def test_invalid_plugin_names_regex():
    """Names that violate the regex are rejected."""
    invalid = [
        "MyPlugin",  # uppercase
        "1plugin",  # starts with digit
        "-plugin",  # starts with hyphen
        "plugin_name",  # underscore
        "plugin name",  # space
        "",  # empty
        "x" * 41,  # too long
        "plugin.name",  # dot
    ]
    for name in invalid:
        with pytest.raises(ValueError):
            validate_plugin_name(name)


def test_reserved_names_rejected():
    """Reserved plugin names raise ValueError."""
    for name in RESERVED_PLUGIN_NAMES:
        with pytest.raises(ValueError, match="reserved"):
            validate_plugin_name(name)


def test_ensure_layout_creates_all_dirs(tmp_path, monkeypatch):
    """ensure_layout() creates the full ~/.nativeagents/ tree idempotently."""
    monkeypatch.setenv("NATIVEAGENTS_HOME", str(tmp_path / "na"))
    ensure_layout()
    na = home()
    assert (na).is_dir()
    assert (na / "plugins").is_dir()
    assert memory_dir().is_dir()
    assert wiki_dir().is_dir()
    assert policies_dir().is_dir()
    assert spool_dir().is_dir()
    assert bin_dir().is_dir()


def test_ensure_layout_idempotent(tmp_path, monkeypatch):
    """ensure_layout() is safe to call multiple times."""
    monkeypatch.setenv("NATIVEAGENTS_HOME", str(tmp_path / "na"))
    ensure_layout()
    ensure_layout()  # must not raise


def test_reserved_prefixes_rejected():
    """Plugin names starting with reserved prefixes are rejected."""
    reserved_prefix_names = ["native-myplugin", "sdk-logger", "system-monitor"]
    for name in reserved_prefix_names:
        with pytest.raises(ValueError, match="reserved prefix"):
            validate_plugin_name(name)
