"""Tests for HookDispatcher."""

from __future__ import annotations

import io
import json
import sys

import pytest

from nativeagents_sdk.hooks.dispatcher import HookDecision, HookDispatcher


def make_payload(
    event_name: str = "PreToolUse",
    session_id: str = "abc123",
    **kwargs,
) -> str:
    data = {
        "hook_event_name": event_name,
        "session_id": session_id,
        "cwd": "/tmp",
        "permission_mode": "allow",
    }
    data.update(kwargs)
    return json.dumps(data)


def test_dispatcher_ok_exits_0(monkeypatch, isolated_home):
    """Handler returning HookDecision.ok() causes exit 0."""
    dispatcher = HookDispatcher(plugin_name="test-plugin")

    @dispatcher.on("PreToolUse")
    def handler(event, ctx):
        return HookDecision.ok()

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(make_payload("PreToolUse", tool_name="Read", tool_input={})),
    )
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        dispatcher.run()
    assert exc_info.value.code == 0


def test_dispatcher_block_exits_2(monkeypatch, isolated_home, capsys):
    """Handler returning HookDecision.block() causes exit 2."""
    dispatcher = HookDispatcher(plugin_name="test-plugin")

    @dispatcher.on("PreToolUse")
    def handler(event, ctx):
        return HookDecision.block("blocked by policy")

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(make_payload("PreToolUse", tool_name="Bash", tool_input={})),
    )
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        dispatcher.run()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "blocked by policy" in captured.err


def test_dispatcher_no_handler_exits_0(monkeypatch, isolated_home):
    """No registered handler for event → exits 0 silently."""
    dispatcher = HookDispatcher(plugin_name="test-plugin")
    # No handlers registered

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(make_payload("PreToolUse", tool_name="Read", tool_input={})),
    )
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        dispatcher.run()
    assert exc_info.value.code == 0


def test_dispatcher_handler_exception_exits_0(monkeypatch, isolated_home):
    """Unhandled exception in handler → logs and exits 0 (never blocks)."""
    dispatcher = HookDispatcher(plugin_name="test-plugin")

    @dispatcher.on("PreToolUse")
    def handler(event, ctx):
        raise RuntimeError("unexpected error")

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(make_payload("PreToolUse", tool_name="Read", tool_input={})),
    )
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        dispatcher.run()
    assert exc_info.value.code == 0


def test_dispatcher_on_decorator():
    """@dispatcher.on() decorator registers handler and returns function."""
    dispatcher = HookDispatcher(plugin_name="test-plugin")

    @dispatcher.on("PreToolUse")
    def handler(event, ctx):
        return HookDecision.ok()

    assert "PreToolUse" in dispatcher._handlers
    assert dispatcher._handlers["PreToolUse"] is handler


def test_hook_decision_ok():
    """HookDecision.ok() has should_block=False."""
    d = HookDecision.ok()
    assert not d.should_block


def test_hook_decision_block():
    """HookDecision.block() has should_block=True and reason set."""
    d = HookDecision.block("policy violation")
    assert d.should_block
    assert d.reason == "policy violation"


def test_dispatcher_multiple_handlers(monkeypatch, isolated_home):
    """Multiple event types can be registered."""
    dispatcher = HookDispatcher(plugin_name="test-plugin")
    called = []

    @dispatcher.on("PreToolUse")
    def handle_pre(event, ctx):
        called.append("pre")
        return HookDecision.ok()

    @dispatcher.on("PostToolUse")
    def handle_post(event, ctx):
        called.append("post")
        return HookDecision.ok()

    # Fire PreToolUse
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(make_payload("PreToolUse", tool_name="Read", tool_input={})),
    )
    monkeypatch.delenv("HOOK_EVENT_NAME", raising=False)

    with pytest.raises(SystemExit):
        dispatcher.run()

    assert "pre" in called
    assert "post" not in called
