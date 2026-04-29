"""Tests for nativeagents_sdk.install.shims."""

from __future__ import annotations

import stat
from pathlib import Path

from nativeagents_sdk.install.shims import (
    shim_is_executable,
    write_capture_shim,
    write_decision_shim,
)

# ---------------------------------------------------------------------------
# write_decision_shim
# ---------------------------------------------------------------------------


def test_write_decision_shim_creates_file(tmp_path: Path) -> None:
    dest = tmp_path / "hooks" / "my-plugin-hook.sh"
    result = write_decision_shim(
        plugin_name="my-plugin",
        python_executable="/usr/bin/python3",
        module="my_plugin.hook",
        dest=dest,
    )
    assert result == dest
    assert dest.exists()


def test_write_decision_shim_substitutes_plugin_name(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_decision_shim("my-plugin", "/usr/bin/python3", "my.hook", dest)
    content = dest.read_text()
    assert "my-plugin" in content


def test_write_decision_shim_substitutes_python(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_decision_shim("p", "/custom/python3", "m", dest)
    assert "/custom/python3" in dest.read_text()


def test_write_decision_shim_substitutes_module(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_decision_shim("p", "/usr/bin/python3", "agentmemory.hook", dest)
    assert "agentmemory.hook" in dest.read_text()


def test_write_decision_shim_is_executable(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_decision_shim("p", "/usr/bin/python3", "m", dest)
    assert dest.stat().st_mode & stat.S_IXUSR


def test_write_decision_shim_is_bash(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_decision_shim("p", "/usr/bin/python3", "m", dest)
    first_line = dest.read_text().splitlines()[0]
    assert first_line.startswith("#!/")


def test_write_decision_shim_creates_parents(tmp_path: Path) -> None:
    dest = tmp_path / "deep" / "nested" / "hook.sh"
    write_decision_shim("p", "/usr/bin/python3", "m", dest)
    assert dest.exists()


def test_write_decision_shim_idempotent(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_decision_shim("p", "/usr/bin/python3", "m", dest)
    c1 = dest.read_text()
    write_decision_shim("p", "/usr/bin/python3", "m", dest)
    c2 = dest.read_text()
    assert c1 == c2


# ---------------------------------------------------------------------------
# write_capture_shim
# ---------------------------------------------------------------------------


def test_write_capture_shim_creates_file(tmp_path: Path) -> None:
    dest = tmp_path / "capture-hook.sh"
    result = write_capture_shim(
        plugin_name="agentaudit",
        python_executable="/usr/bin/python3",
        spool_dir=tmp_path / "spool",
        drain_module="agentaudit.drain",
        dest=dest,
    )
    assert result == dest
    assert dest.exists()


def test_write_capture_shim_is_executable(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_capture_shim("p", "/usr/bin/python3", tmp_path / "spool", "p.drain", dest)
    assert dest.stat().st_mode & stat.S_IXUSR


def test_write_capture_shim_contains_spool_dir(tmp_path: Path) -> None:
    spool = tmp_path / "my-spool"
    dest = tmp_path / "hook.sh"
    write_capture_shim("p", "/usr/bin/python3", spool, "p.drain", dest)
    assert str(spool) in dest.read_text()


def test_write_capture_shim_contains_drain_module(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_capture_shim("p", "/usr/bin/python3", tmp_path / "spool", "agentaudit.drain", dest)
    assert "agentaudit.drain" in dest.read_text()


def test_write_capture_shim_with_daemon_sock(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    sock = tmp_path / "capture.sock"
    write_capture_shim(
        "p", "/usr/bin/python3", tmp_path / "spool", "p.drain", dest, daemon_sock=sock
    )
    assert str(sock) in dest.read_text()


def test_write_capture_shim_always_exits_zero(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_capture_shim("p", "/usr/bin/python3", tmp_path / "spool", "p.drain", dest)
    content = dest.read_text()
    assert "exit 0" in content


def test_write_capture_shim_is_bash(tmp_path: Path) -> None:
    dest = tmp_path / "hook.sh"
    write_capture_shim("p", "/usr/bin/python3", tmp_path / "spool", "p.drain", dest)
    assert dest.read_text().splitlines()[0].startswith("#!/")


def test_write_capture_shim_creates_parents(tmp_path: Path) -> None:
    dest = tmp_path / "deep" / "nested" / "hook.sh"
    write_capture_shim("p", "/usr/bin/python3", tmp_path / "spool", "p.drain", dest)
    assert dest.exists()


# ---------------------------------------------------------------------------
# shim_is_executable
# ---------------------------------------------------------------------------


def test_shim_is_executable_true(tmp_path: Path) -> None:
    f = tmp_path / "script.sh"
    f.write_text("#!/bin/bash\n")
    f.chmod(0o755)
    assert shim_is_executable(f) is True


def test_shim_is_executable_false_no_exec(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("data")
    f.chmod(0o644)
    assert shim_is_executable(f) is False


def test_shim_is_executable_missing_file(tmp_path: Path) -> None:
    assert shim_is_executable(tmp_path / "nonexistent.sh") is False
