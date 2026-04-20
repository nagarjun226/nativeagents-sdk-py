"""Tests for nativeagents_sdk.config module."""

import pytest

from nativeagents_sdk.config import (
    AuditConfig,
    Config,
    LoggingConfig,
    load_config,
    save_config,
    validate_config,
)
from nativeagents_sdk.errors import ConfigError
from nativeagents_sdk.paths import config_path


def test_load_config_missing_file(isolated_home):
    """load_config() returns defaults when file doesn't exist."""
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.schema_version == 1
    assert cfg.audit.enabled is True
    assert cfg.logging.level == "INFO"


def test_load_config_from_path(tmp_path):
    """load_config() loads from explicit path."""
    p = tmp_path / "config.yaml"
    p.write_text("schema_version: 1\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.schema_version == 1


def test_save_and_load_roundtrip(isolated_home):
    """save_config() + load_config() round-trips the model."""
    cfg = Config(
        schema_version=1,
        logging=LoggingConfig(level="DEBUG"),
        audit=AuditConfig(enabled=False, verify_on_startup=True),
        plugins={"my-plugin": {"key": "value"}},
    )
    save_config(cfg)
    loaded = load_config()
    assert loaded.logging.level == "DEBUG"
    assert loaded.audit.enabled is False
    assert loaded.audit.verify_on_startup is True
    assert loaded.plugins.get("my-plugin") == {"key": "value"}


def test_load_config_ignores_unknown_fields(tmp_path):
    """Forward-compat: unknown fields are ignored."""
    p = tmp_path / "config.yaml"
    p.write_text(
        "schema_version: 1\nunknown_future_field: 42\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.schema_version == 1


def test_load_config_invalid_yaml(tmp_path):
    """Invalid YAML raises ConfigError."""
    p = tmp_path / "config.yaml"
    p.write_text("{invalid: yaml: content", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML"):
        load_config(p)


def test_load_config_non_mapping(tmp_path):
    """Non-mapping YAML raises ConfigError."""
    p = tmp_path / "config.yaml"
    p.write_text("- list\n- item\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_validate_config_too_new():
    """schema_version > max raises ConfigError."""
    with pytest.raises(ConfigError, match="schema_version"):
        validate_config({"schema_version": 999})


def test_validate_config_valid():
    """Valid dict passes validation."""
    cfg = validate_config({"schema_version": 1, "audit": {"enabled": True}})
    assert cfg.audit.enabled is True


def test_save_config_atomic(isolated_home):
    """save_config() writes atomically (no .tmp files left behind)."""
    cfg = Config()
    save_config(cfg)
    path = config_path()
    assert path.exists()
    # No .tmp files
    tmp_files = list(path.parent.glob("*.tmp*"))
    assert tmp_files == []


def test_config_empty_yaml(tmp_path):
    """Empty YAML file returns defaults."""
    p = tmp_path / "config.yaml"
    p.write_text("", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.schema_version == 1
