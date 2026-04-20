"""Config file loading and validation for the Native Agents SDK.

Config lives at ~/.nativeagents/config.yaml (or NATIVEAGENTS_HOME/config.yaml).
If the file doesn't exist, load_config() returns safe defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from nativeagents_sdk.errors import ConfigError

MAX_SUPPORTED_SCHEMA_VERSION = 1


class LoggingConfig(BaseModel):
    """Logging configuration block."""

    model_config = ConfigDict(extra="ignore")

    level: str = "INFO"
    directory: str = "~/.nativeagents/logs"


class AuditConfig(BaseModel):
    """Audit subsystem configuration block."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    verify_on_startup: bool = False


class SidecarConfig(BaseModel):
    """Reserved for future paid sidecar use — ignored in OSS."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False


class Config(BaseModel):
    """Top-level SDK configuration model.

    Corresponds to ~/.nativeagents/config.yaml.
    Unknown fields at the top level are ignored for forward-compatibility.
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    logging: LoggingConfig = LoggingConfig()
    audit: AuditConfig = AuditConfig()
    plugins: dict[str, Any] = {}
    sidecar: SidecarConfig = SidecarConfig()


def load_config(path: Path | None = None) -> Config:
    """Load config from disk, returning defaults if the file does not exist.

    Args:
        path: Path to config.yaml. If None, uses paths.config_path().

    Returns:
        Config model with defaults for any missing fields.

    Raises:
        ConfigError: If the file exists but cannot be parsed or is invalid.
    """
    if path is None:
        from nativeagents_sdk.paths import config_path

        path = config_path()

    if not path.exists():
        return Config()

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc

    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config file {path} is not valid YAML: {exc}") from exc

    if raw is None:
        return Config()

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file {path} must be a YAML mapping, got {type(raw).__name__}")

    return validate_config(raw)


def save_config(config: Config, path: Path | None = None) -> None:
    """Write config to disk atomically.

    Args:
        config: Config model to write.
        path: Destination path. If None, uses paths.config_path().
    """
    if path is None:
        from nativeagents_sdk.paths import config_path

        path = config_path()

    from nativeagents_sdk.paths import atomic_write

    data = yaml.dump(
        config.model_dump(),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
    )
    atomic_write(path, data.encode("utf-8"))


def validate_config(raw: dict[str, Any]) -> Config:
    """Parse and validate a raw dict into a Config model.

    Args:
        raw: Dictionary from YAML deserialization.

    Returns:
        Validated Config model.

    Raises:
        ConfigError: If the dict does not conform to the Config schema.
    """
    schema_version = raw.get("schema_version", 1)
    if isinstance(schema_version, int) and schema_version > MAX_SUPPORTED_SCHEMA_VERSION:
        raise ConfigError(
            f"Config schema_version {schema_version} is newer than this SDK supports "
            f"(max {MAX_SUPPORTED_SCHEMA_VERSION}). Upgrade nativeagents-sdk."
        )

    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Config validation failed: {exc}") from exc
