"""Plugin manifest loading and discovery."""

from nativeagents_sdk.plugin.discovery import discover_plugins, resolve_plugin
from nativeagents_sdk.plugin.manifest import load_plugin_manifest, save_plugin_manifest

__all__ = [
    "load_plugin_manifest",
    "save_plugin_manifest",
    "discover_plugins",
    "resolve_plugin",
]
