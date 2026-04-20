"""Tests for plugin registration in ~/.claude/settings.json."""

from __future__ import annotations

from nativeagents_sdk.install.register import (
    is_registered,
    read_claude_settings,
    register_plugin,
    unregister_plugin,
    write_claude_settings,
)


def make_manifest(name: str = "test-plugin", hooks: list | None = None):
    """Create a minimal PluginManifest for testing."""
    from nativeagents_sdk.schema.plugin import PluginManifest

    return PluginManifest(
        schema_version=1,
        name=name,
        version="0.1.0",
        description="Test plugin",
        hooks=hooks or ["PreToolUse", "SessionStart"],
        writes_audit_events=True,
        owns_paths=[f"plugins/{name}/"],
        hook_module=f"{name.replace('-', '_')}.hook",
    )


def test_read_settings_missing_returns_default(isolated_home):
    """read_claude_settings() returns {'hooks': {}} when file doesn't exist."""
    settings = read_claude_settings()
    assert settings == {"hooks": {}}


def test_write_and_read_settings(isolated_home):
    """write_claude_settings() + read_claude_settings() round-trip."""
    settings = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": []}]}}
    write_claude_settings(settings)
    loaded = read_claude_settings()
    assert loaded["hooks"]["PreToolUse"][0]["matcher"] == "*"


def test_register_plugin_creates_entries(isolated_home, tmp_path):
    """register_plugin() adds hook entries for all declared events."""
    manifest = make_manifest(hooks=["PreToolUse", "SessionStart"])
    hook_script = tmp_path / "hook.sh"
    hook_script.write_text("#!/bin/bash\n")

    register_plugin(manifest, hook_script)
    settings = read_claude_settings()

    assert "PreToolUse" in settings["hooks"]
    assert "SessionStart" in settings["hooks"]


def test_register_plugin_idempotent(isolated_home, tmp_path):
    """Calling register_plugin() twice doesn't duplicate entries."""
    manifest = make_manifest(hooks=["PreToolUse"])
    hook_script = tmp_path / "hook.sh"
    hook_script.write_text("#!/bin/bash\n")

    register_plugin(manifest, hook_script)
    register_plugin(manifest, hook_script)  # Second call

    settings = read_claude_settings()
    entries = settings["hooks"]["PreToolUse"]
    # Should only have one entry for our plugin
    our_entries = [
        h
        for group in entries
        for h in group.get("hooks", [])
        if h.get("nativeagents_plugin") == "test-plugin"
    ]
    assert len(our_entries) == 1


def test_register_plugin_preserves_existing_entries(isolated_home, tmp_path):
    """register_plugin() doesn't remove user-added entries."""
    # Pre-populate settings with a user entry
    existing = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "*", "hooks": [{"type": "command", "command": "/user/hook.sh"}]}
            ]
        }
    }
    write_claude_settings(existing)

    manifest = make_manifest(hooks=["PreToolUse"])
    hook_script = tmp_path / "hook.sh"
    hook_script.write_text("#!/bin/bash\n")
    register_plugin(manifest, hook_script)

    settings = read_claude_settings()
    entries = settings["hooks"]["PreToolUse"]
    # Should have both the user entry and our entry
    all_hooks = [h for group in entries for h in group.get("hooks", [])]
    commands = [h.get("command") for h in all_hooks]
    assert "/user/hook.sh" in commands
    assert str(hook_script) in commands


def test_unregister_plugin_removes_entries(isolated_home, tmp_path):
    """unregister_plugin() removes SDK-managed entries."""
    manifest = make_manifest(hooks=["PreToolUse"])
    hook_script = tmp_path / "hook.sh"
    hook_script.write_text("#!/bin/bash\n")

    register_plugin(manifest, hook_script)
    assert is_registered("test-plugin")

    unregister_plugin("test-plugin")
    assert not is_registered("test-plugin")


def test_unregister_nonexistent_is_noop(isolated_home):
    """unregister_plugin() of an unregistered plugin is a no-op."""
    unregister_plugin("nonexistent-plugin")  # Should not raise


def test_unregister_preserves_other_plugins(isolated_home, tmp_path):
    """unregister_plugin() only removes entries for the specified plugin."""
    hook_a = tmp_path / "hook_a.sh"
    hook_a.write_text("#!/bin/bash\n")
    hook_b = tmp_path / "hook_b.sh"
    hook_b.write_text("#!/bin/bash\n")

    register_plugin(make_manifest("plugin-a", hooks=["PreToolUse"]), hook_a)
    register_plugin(make_manifest("plugin-b", hooks=["PreToolUse"]), hook_b)

    unregister_plugin("plugin-a")

    assert not is_registered("plugin-a")
    assert is_registered("plugin-b")


def test_is_registered_false_initially(isolated_home):
    """is_registered() returns False before registration."""
    assert not is_registered("test-plugin")


def test_register_creates_plugin_dir(isolated_home, tmp_path):
    """register_plugin() creates the plugin state directory."""
    from nativeagents_sdk.paths import plugin_dir

    manifest = make_manifest(hooks=["PreToolUse"])
    hook_script = tmp_path / "hook.sh"
    hook_script.write_text("#!/bin/bash\n")

    register_plugin(manifest, hook_script)
    p_dir = plugin_dir("test-plugin")
    assert p_dir.exists()
    assert (p_dir / "logs").exists()


def test_register_creates_backup(isolated_home, tmp_path):
    """register_plugin() creates a timestamped backup of settings.json."""
    from nativeagents_sdk.paths import claude_home

    manifest = make_manifest(hooks=["PreToolUse"])
    hook_script = tmp_path / "hook.sh"
    hook_script.write_text("#!/bin/bash\n")

    # Create initial settings
    write_claude_settings({"hooks": {}})
    register_plugin(manifest, hook_script)

    bak_files = list((claude_home()).glob("settings.json.bak.*"))
    assert len(bak_files) >= 1


def test_backup_rolling_cap(isolated_home, tmp_path):
    """register_plugin() keeps at most _MAX_BACKUPS backup files."""
    from nativeagents_sdk.install.register import _MAX_BACKUPS
    from nativeagents_sdk.paths import claude_home

    hook_script = tmp_path / "hook.sh"
    hook_script.write_text("#!/bin/bash\n")

    write_claude_settings({"hooks": {}})

    # Call register _MAX_BACKUPS + 3 times to exceed the cap.
    for i in range(_MAX_BACKUPS + 3):
        manifest = make_manifest(name=f"cap-plugin-{i}", hooks=["SessionStart"])
        register_plugin(manifest, hook_script)

    bak_files = list((claude_home()).glob("settings.json.bak.*"))
    assert len(bak_files) <= _MAX_BACKUPS
