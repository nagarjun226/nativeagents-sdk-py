"""Load and save plugin.toml manifests."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import tomli_w
from pydantic import ValidationError

from nativeagents_sdk.errors import PluginManifestError
from nativeagents_sdk.schema.plugin import PluginManifest, PluginRequires

MAX_SUPPORTED_SCHEMA_VERSION = 1


def load_plugin_manifest(path: Path) -> PluginManifest:
    """Load and validate a plugin.toml file.

    Args:
        path: Path to plugin.toml.

    Returns:
        Validated PluginManifest model.

    Raises:
        PluginManifestError: If the file doesn't exist, has invalid TOML,
            or fails validation.
    """
    if not path.exists():
        raise PluginManifestError(f"Plugin manifest not found: {path}")

    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise PluginManifestError(f"Cannot read plugin manifest {path}: {exc}") from exc

    try:
        raw: Any = tomllib.loads(raw_bytes.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PluginManifestError(f"Plugin manifest {path} is not valid TOML: {exc}") from exc

    if not isinstance(raw, dict):
        raise PluginManifestError(f"Plugin manifest {path} must be a TOML table")

    schema_version = raw.get("schema_version", 1)
    if isinstance(schema_version, int) and schema_version > MAX_SUPPORTED_SCHEMA_VERSION:
        raise PluginManifestError(
            f"Plugin manifest schema_version {schema_version} is newer than this SDK supports "
            f"(max {MAX_SUPPORTED_SCHEMA_VERSION}). Upgrade nativeagents-sdk."
        )

    # plugin.toml has a [plugin] section; flatten it for the model
    plugin_section: dict[str, Any] = raw.get("plugin", {})

    # Build the dict for PluginManifest
    manifest_data: dict[str, Any] = {"schema_version": schema_version}
    manifest_data.update(plugin_section)

    # Handle nested [plugin.requires]
    requires_raw = plugin_section.get("requires", {})
    if requires_raw:
        manifest_data["requires"] = requires_raw
    else:
        manifest_data["requires"] = PluginRequires()

    try:
        return PluginManifest.model_validate(manifest_data)
    except ValidationError as exc:
        raise PluginManifestError(f"Plugin manifest {path} validation failed: {exc}") from exc


def save_plugin_manifest(path: Path, m: PluginManifest) -> None:
    """Write a plugin manifest as TOML atomically.

    Args:
        path: Destination path (e.g., plugin.toml or plugins/<name>/plugin.toml).
        m: PluginManifest model to write.

    Raises:
        PluginManifestError: On write failure.
    """
    from nativeagents_sdk.paths import atomic_write

    # Build the TOML structure: top-level schema_version + [plugin] table
    plugin_dict: dict[str, Any] = {
        "name": m.name,
        "version": m.version,
        "description": m.description,
    }
    if m.homepage is not None:
        plugin_dict["homepage"] = m.homepage
    plugin_dict["license"] = m.license
    if m.authors:
        plugin_dict["authors"] = m.authors
    if m.well_known_namespace is not None:
        plugin_dict["well_known_namespace"] = m.well_known_namespace
    if m.hooks:
        plugin_dict["hooks"] = m.hooks
    if m.owns_paths:
        plugin_dict["owns_paths"] = m.owns_paths
    plugin_dict["writes_audit_events"] = m.writes_audit_events
    if m.produces_spool_kinds:
        plugin_dict["produces_spool_kinds"] = m.produces_spool_kinds
    if m.cli_entry is not None:
        plugin_dict["cli_entry"] = m.cli_entry
    if m.hook_module is not None:
        plugin_dict["hook_module"] = m.hook_module
    if m.min_sdk_version is not None:
        plugin_dict["min_sdk_version"] = m.min_sdk_version
    if m.max_sdk_version is not None:
        plugin_dict["max_sdk_version"] = m.max_sdk_version

    # Add requires section if non-default
    requires = m.requires
    if requires.optional or requires.required:
        plugin_dict["requires"] = {}
        if requires.optional:
            plugin_dict["requires"]["optional"] = requires.optional
        if requires.required:
            plugin_dict["requires"]["required"] = requires.required

    toml_data: dict[str, Any] = {
        "schema_version": m.schema_version,
        "plugin": plugin_dict,
    }

    try:
        data = tomli_w.dumps(toml_data)
        atomic_write(path, data.encode("utf-8"))
    except OSError as exc:
        raise PluginManifestError(f"Failed to write plugin manifest to {path}: {exc}") from exc
