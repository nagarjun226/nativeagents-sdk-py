"""Plugin discovery: scan installed plugins from ~/.nativeagents/."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nativeagents_sdk.errors import DuplicatePluginError, PluginManifestError

if TYPE_CHECKING:
    from nativeagents_sdk.schema.plugin import PluginManifest

logger = logging.getLogger(__name__)


def discover_plugins() -> list[PluginManifest]:
    """Discover all installed plugins by scanning the filesystem.

    Scans:
    - ~/.nativeagents/plugins/*/plugin.toml
    - ~/.nativeagents/memory/plugin.toml
    - ~/.nativeagents/wiki/plugin.toml

    Malformed manifests are logged and skipped (never raise).

    Returns:
        List of valid PluginManifest instances.

    Raises:
        DuplicatePluginError: If two manifests declare the same plugin name.
    """
    from nativeagents_sdk.paths import home, memory_dir, wiki_dir
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest

    manifests: dict[str, PluginManifest] = {}  # name -> manifest
    manifest_paths: dict[str, str] = {}  # name -> path (for error messages)

    candidate_paths = []

    # Scan plugins/ subdirectories
    plugins_root = home() / "plugins"
    if plugins_root.exists():
        for entry in sorted(plugins_root.iterdir()):
            if entry.is_dir():
                toml_path = entry / "plugin.toml"
                if toml_path.exists():
                    candidate_paths.append(toml_path)

    # Scan well-known namespaces
    for wk_dir in [memory_dir(), wiki_dir()]:
        toml_path = wk_dir / "plugin.toml"
        if toml_path.exists():
            candidate_paths.append(toml_path)

    for path in candidate_paths:
        try:
            manifest = load_plugin_manifest(path)
        except PluginManifestError as exc:
            logger.warning("Skipping malformed plugin manifest %s: %s", path, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error loading plugin manifest %s: %s", path, exc)
            continue

        name = manifest.name
        if name in manifests:
            raise DuplicatePluginError(
                f"Duplicate plugin name {name!r}: found in both {manifest_paths[name]} and {path}"
            )

        manifests[name] = manifest
        manifest_paths[name] = str(path)

    return list(manifests.values())


def resolve_plugin(name: str) -> PluginManifest | None:
    """Look up a specific plugin by name.

    Args:
        name: Plugin name to look up.

    Returns:
        PluginManifest if found, None otherwise.

    Raises:
        DuplicatePluginError: If the name appears in multiple manifest files.
    """
    from nativeagents_sdk.paths import memory_dir, plugin_dir, wiki_dir
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest

    candidates = [
        plugin_dir(name) / "plugin.toml",
        memory_dir() / "plugin.toml",
        wiki_dir() / "plugin.toml",
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            manifest = load_plugin_manifest(path)
            if manifest.name == name:
                return manifest
        except PluginManifestError:
            continue

    return None
