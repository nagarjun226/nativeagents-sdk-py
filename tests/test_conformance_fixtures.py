"""Tests for conformance.fixtures module."""

from __future__ import annotations

import json


def test_session_start_payload() -> None:
    """session_start_payload() returns a valid SessionStart event dict."""
    from nativeagents_sdk.conformance.fixtures import session_start_payload

    p = session_start_payload()
    assert p["hook_event_name"] == "SessionStart"
    assert "session_id" in p
    assert "cwd" in p


def test_session_start_payload_custom_session_id() -> None:
    """session_start_payload() accepts a custom session_id."""
    from nativeagents_sdk.conformance.fixtures import session_start_payload

    p = session_start_payload(session_id="my-custom-session")
    assert p["session_id"] == "my-custom-session"


def test_pre_tool_use_payload() -> None:
    """pre_tool_use_payload() returns a valid PreToolUse event dict."""
    from nativeagents_sdk.conformance.fixtures import pre_tool_use_payload

    p = pre_tool_use_payload()
    assert p["hook_event_name"] == "PreToolUse"
    assert p["tool_name"] == "Read"
    assert "tool_input" in p


def test_pre_tool_use_payload_custom_args() -> None:
    """pre_tool_use_payload() accepts custom tool_name and tool_input."""
    from nativeagents_sdk.conformance.fixtures import pre_tool_use_payload

    p = pre_tool_use_payload(tool_name="Bash", tool_input={"command": "ls"})
    assert p["tool_name"] == "Bash"
    assert p["tool_input"] == {"command": "ls"}


def test_post_tool_use_payload() -> None:
    """post_tool_use_payload() returns a valid PostToolUse event dict."""
    from nativeagents_sdk.conformance.fixtures import post_tool_use_payload

    p = post_tool_use_payload()
    assert p["hook_event_name"] == "PostToolUse"
    assert "tool_result" in p


def test_post_tool_use_payload_custom_result() -> None:
    """post_tool_use_payload() accepts a custom tool_result."""
    from nativeagents_sdk.conformance.fixtures import post_tool_use_payload

    p = post_tool_use_payload(tool_result={"output": "hello"})
    assert p["tool_result"] == {"output": "hello"}


def test_stop_payload() -> None:
    """stop_payload() returns a valid Stop event dict."""
    from nativeagents_sdk.conformance.fixtures import stop_payload

    p = stop_payload()
    assert p["hook_event_name"] == "Stop"
    assert p["reason"] == "completed"


def test_all_fixtures_returns_list() -> None:
    """all_fixtures() returns a list of 4 hook event payloads."""
    from nativeagents_sdk.conformance.fixtures import all_fixtures

    fixtures = all_fixtures()
    assert len(fixtures) == 4
    event_names = {f["hook_event_name"] for f in fixtures}
    assert "SessionStart" in event_names
    assert "PreToolUse" in event_names
    assert "PostToolUse" in event_names
    assert "Stop" in event_names


def test_fixture_as_json() -> None:
    """fixture_as_json() serializes a payload to a JSON string."""
    from nativeagents_sdk.conformance.fixtures import fixture_as_json, pre_tool_use_payload

    p = pre_tool_use_payload()
    result = fixture_as_json(p)
    # Should be valid JSON
    parsed = json.loads(result)
    assert parsed["hook_event_name"] == "PreToolUse"
