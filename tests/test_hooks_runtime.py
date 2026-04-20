"""Tests for hooks runtime utilities."""

from __future__ import annotations

import io
import json
import sys

import pytest

from nativeagents_sdk.schema.events import PreToolUseInput


def test_read_hook_input_from_stdin(monkeypatch):
    """read_hook_input() parses JSON from stdin."""
    from nativeagents_sdk.hooks.runtime import read_hook_input

    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "abc123",
        "cwd": "/tmp",
        "permission_mode": "allow",
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.txt"},
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    result = read_hook_input()
    assert isinstance(result, PreToolUseInput)
    assert result.tool_name == "Read"


def test_read_hook_input_env_overrides_payload(monkeypatch):
    """HOOK_EVENT_NAME env var takes precedence over hook_event_name in payload."""
    from nativeagents_sdk.hooks.runtime import read_hook_input

    payload = {
        "hook_event_name": "SessionStart",  # would normally parse as SessionStart
        "session_id": "abc123",
        "cwd": "/tmp",
        "permission_mode": "allow",
        "tool_name": "Read",
        "tool_input": {},
    }
    # But env says PreToolUse
    monkeypatch.setenv("HOOK_EVENT_NAME", "PreToolUse")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    result = read_hook_input()
    assert isinstance(result, PreToolUseInput)


def test_read_hook_input_invalid_json_exits(monkeypatch):
    """Invalid JSON on stdin causes SystemExit(1)."""
    from nativeagents_sdk.hooks.runtime import read_hook_input

    monkeypatch.setattr(sys, "stdin", io.StringIO("{not valid json"))
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        read_hook_input()
    assert exc_info.value.code == 1


def test_ok_exits_0():
    """ok() raises SystemExit(0)."""
    from nativeagents_sdk.hooks.runtime import ok

    with pytest.raises(SystemExit) as exc_info:
        ok()
    assert exc_info.value.code == 0


def test_fail_exits_0():
    """fail() logs and exits 0 (never blocks)."""
    from nativeagents_sdk.hooks.runtime import fail

    with pytest.raises(SystemExit) as exc_info:
        fail("test error")
    assert exc_info.value.code == 0


def test_block_exits_2(capsys):
    """block() prints to stderr and exits 2."""
    from nativeagents_sdk.hooks.runtime import block

    with pytest.raises(SystemExit) as exc_info:
        block("policy violation: unsafe tool")
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "policy violation" in captured.err
