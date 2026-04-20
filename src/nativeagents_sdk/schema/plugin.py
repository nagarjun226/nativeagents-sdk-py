"""Pydantic models for plugin.toml manifests."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from nativeagents_sdk.paths import _PLUGIN_NAME_RE, _RESERVED_PLUGIN_PREFIXES, RESERVED_PLUGIN_NAMES

# Simplified SemVer regex: MAJOR.MINOR.PATCH with optional pre-release/build metadata
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?$"
)

VALID_HOOK_EVENTS: frozenset[str] = frozenset(
    [
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "SubagentStop",
        "Stop",
        "Notification",
        "PreCompact",
        "PostCompact",
        "SessionEnd",
    ]
)


class PluginRequires(BaseModel):
    """Dependencies section of a plugin manifest."""

    model_config = ConfigDict(extra="ignore")

    optional: list[str] = []
    required: list[str] = []


class PluginManifest(BaseModel):
    """Pydantic model for plugin.toml.

    Top-level TOML structure:
        schema_version = 1
        [plugin]
        name = "..."
        ...
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    name: str
    version: str
    description: str
    homepage: str | None = None
    license: str = "MIT"
    authors: list[str] = []
    well_known_namespace: str | None = None
    hooks: list[str] = []
    owns_paths: list[str] = []
    writes_audit_events: bool = False
    produces_spool_kinds: list[str] = []
    cli_entry: str | None = None
    hook_module: str | None = None
    min_sdk_version: str | None = None
    max_sdk_version: str | None = None
    requires: PluginRequires = PluginRequires()

    # Allow arbitrary extra fields from plugin section for forward compat
    extra_fields: dict[str, Any] = {}

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        """Validate plugin name format and reserved-name exclusions."""
        if not _PLUGIN_NAME_RE.match(v):
            raise ValueError(f"Invalid plugin name {v!r}. Must match ^[a-z][a-z0-9-]{{{{0,39}}}}$")
        if v in RESERVED_PLUGIN_NAMES:
            raise ValueError(
                f"Plugin name {v!r} is reserved. Reserved names: {sorted(RESERVED_PLUGIN_NAMES)}"
            )
        for prefix in _RESERVED_PLUGIN_PREFIXES:
            if v.startswith(prefix):
                raise ValueError(
                    f"Plugin name {v!r} uses a reserved prefix {prefix!r}."
                )
        return v

    @field_validator("version", "min_sdk_version", "max_sdk_version")
    @classmethod
    def _validate_semver(cls, v: str | None) -> str | None:
        """Validate version strings are SemVer-compliant."""
        if v is None:
            return v
        if not _SEMVER_RE.match(v):
            raise ValueError(
                f"Version {v!r} is not a valid SemVer string (expected MAJOR.MINOR.PATCH[-pre])."
            )
        return v

    @field_validator("hooks")
    @classmethod
    def _validate_hooks(cls, v: list[str]) -> list[str]:
        """Validate that all declared hooks are recognised Claude Code event names."""
        invalid = [h for h in v if h not in VALID_HOOK_EVENTS]
        if invalid:
            raise ValueError(
                f"Invalid hook event names: {invalid}. Valid names: {sorted(VALID_HOOK_EVENTS)}"
            )
        return v
