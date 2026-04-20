"""Plugin registration into ~/.claude/settings.json.

All operations are idempotent: registering/unregistering N times produces
the same final state as doing it once.
"""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from nativeagents_sdk.errors import InstallError

logger = logging.getLogger(__name__)

# The marker field we add to every hook entry we manage.
_SDK_MARKER = "nativeagents_plugin"


def _settings_path() -> Path:
    """Return the path to ~/.claude/settings.json."""
    from nativeagents_sdk.paths import claude_home

    return claude_home() / "settings.json"


def read_claude_settings() -> dict[str, Any]:
    """Read ~/.claude/settings.json, returning {} if missing.

    Returns:
        Parsed settings dict. Always has a "hooks" key (at minimum).

    Raises:
        InstallError: If the file exists but cannot be parsed.
    """
    path = _settings_path()
    if not path.exists():
        return {"hooks": {}}

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InstallError(f"Cannot read Claude settings at {path}: {exc}") from exc

    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InstallError(f"Claude settings at {path} is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise InstallError(f"Claude settings at {path} must be a JSON object")

    data.setdefault("hooks", {})
    return data


def write_claude_settings(settings: dict[str, Any]) -> None:
    """Write settings back to ~/.claude/settings.json atomically.

    Args:
        settings: Updated settings dict.

    Raises:
        InstallError: On write failure.
    """
    from nativeagents_sdk.paths import atomic_write

    path = _settings_path()
    try:
        data = json.dumps(settings, indent=2, ensure_ascii=False)
        atomic_write(path, data.encode("utf-8"))
    except OSError as exc:
        raise InstallError(f"Failed to write Claude settings to {path}: {exc}") from exc


_MAX_BACKUPS = 5


def _backup_settings(settings: dict[str, Any]) -> None:
    """Write a timestamped backup of the settings file, keeping at most _MAX_BACKUPS."""
    from nativeagents_sdk.paths import atomic_write, claude_home

    home = claude_home()
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = home / f"settings.json.bak.{ts}"
    try:
        data = json.dumps(settings, indent=2, ensure_ascii=False)
        atomic_write(backup_path, data.encode("utf-8"))
    except OSError as exc:
        logger.warning("Could not create settings backup at %s: %s", backup_path, exc)
        return

    # Prune oldest backups beyond the rolling cap.
    backups = sorted(home.glob("settings.json.bak.*"))
    for old in backups[: max(0, len(backups) - _MAX_BACKUPS)]:
        with contextlib.suppress(OSError):
            old.unlink()


def register_plugin(
    manifest: Any,  # PluginManifest — typed as Any to avoid circular import
    hook_script: Path,
) -> None:
    """Register a plugin's hooks in ~/.claude/settings.json.

    Algorithm:
    1. Read current settings (or start with {}).
    2. Backup current settings.
    3. For each event in manifest.hooks:
       - Ensure hooks[event] is a list.
       - Skip if our nativeagents_plugin entry already exists (idempotent).
       - Otherwise append a new entry with the nativeagents_plugin marker.
    4. Atomic write back.
    5. Copy plugin.toml to ~/.nativeagents/plugins/<name>/.
    6. Create plugin state dir and logs/ subdir.

    Args:
        manifest: PluginManifest for the plugin being registered.
        hook_script: Absolute path to the plugin's hook.sh script.

    Raises:
        InstallError: On failure.
    """
    from nativeagents_sdk.paths import ensure_dir, plugin_dir

    plugin_name = manifest.name

    settings = read_claude_settings()
    _backup_settings(settings)

    hooks_section: dict[str, Any] = settings.setdefault("hooks", {})

    for event_name in manifest.hooks:
        event_entries: list[Any] = hooks_section.setdefault(event_name, [])

        # Check idempotency: already registered?
        already = False
        for group in event_entries:
            if isinstance(group, dict):
                for hook in group.get("hooks", []):
                    if isinstance(hook, dict) and hook.get(_SDK_MARKER) == plugin_name:
                        already = True
                        break
            if already:
                break

        if already:
            logger.debug("Plugin %r already registered for %s; skipping", plugin_name, event_name)
            continue

        # Append new entry
        new_entry: dict[str, Any] = {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": str(hook_script),
                    _SDK_MARKER: plugin_name,
                }
            ],
        }
        event_entries.append(new_entry)

    write_claude_settings(settings)

    # Copy plugin.toml into the plugin state dir
    p_dir = plugin_dir(plugin_name)
    ensure_dir(p_dir / "logs")

    # If the manifest came from a file, copy it over
    dest_toml = p_dir / "plugin.toml"
    if not dest_toml.exists():
        try:
            from nativeagents_sdk.plugin.manifest import save_plugin_manifest

            save_plugin_manifest(dest_toml, manifest)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not copy plugin.toml to %s: %s", dest_toml, exc)


def unregister_plugin(plugin_name: str) -> None:
    """Remove all SDK-managed hook entries for a plugin from settings.json.

    Does NOT delete plugin state directories. Idempotent.

    Args:
        plugin_name: Name of the plugin to unregister.

    Raises:
        InstallError: On read/write failure.
    """
    settings = read_claude_settings()
    _backup_settings(settings)

    hooks_section: dict[str, Any] = settings.get("hooks", {})
    new_hooks: dict[str, Any] = {}

    for event_name, entries in hooks_section.items():
        if not isinstance(entries, list):
            new_hooks[event_name] = entries
            continue

        new_entries = []
        for group in entries:
            if not isinstance(group, dict):
                new_entries.append(group)
                continue

            # Filter hooks within this group
            remaining_hooks = [
                h
                for h in group.get("hooks", [])
                if not (isinstance(h, dict) and h.get(_SDK_MARKER) == plugin_name)
            ]

            if remaining_hooks:
                new_group = dict(group)
                new_group["hooks"] = remaining_hooks
                new_entries.append(new_group)
            # else: entire group was ours — drop it

        if new_entries:
            new_hooks[event_name] = new_entries
        # else: event had no entries left — drop it (prune empty arrays)

    settings["hooks"] = new_hooks
    write_claude_settings(settings)


def is_registered(plugin_name: str) -> bool:
    """Check if a plugin is registered in ~/.claude/settings.json.

    Args:
        plugin_name: Plugin name to look up.

    Returns:
        True if at least one SDK-managed hook entry exists for the plugin.
    """
    try:
        settings = read_claude_settings()
    except InstallError:
        return False

    hooks_section: dict[str, Any] = settings.get("hooks", {})
    for entries in hooks_section.values():
        if not isinstance(entries, list):
            continue
        for group in entries:
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks", []):
                if isinstance(hook, dict) and hook.get(_SDK_MARKER) == plugin_name:
                    return True
    return False
