"""Shared hook-event fixtures for conformance testing."""

from __future__ import annotations

import json
from typing import Any


def session_start_payload(session_id: str = "test-session-001") -> dict[str, Any]:
    """Return a realistic SessionStart hook payload."""
    return {
        "hook_event_name": "SessionStart",
        "session_id": session_id,
        "cwd": "/tmp/test-project",
        "permission_mode": "allow",
        "transcript_path": f"/tmp/.claude/projects/test/{session_id}.jsonl",
    }


def pre_tool_use_payload(
    session_id: str = "test-session-001",
    tool_name: str = "Read",
    tool_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a realistic PreToolUse hook payload."""
    if tool_input is None:
        tool_input = {"file_path": "/tmp/test.txt"}
    return {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "cwd": "/tmp/test-project",
        "permission_mode": "allow",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def post_tool_use_payload(
    session_id: str = "test-session-001",
    tool_name: str = "Read",
    tool_input: dict[str, Any] | None = None,
    tool_result: Any = "file contents",
) -> dict[str, Any]:
    """Return a realistic PostToolUse hook payload."""
    if tool_input is None:
        tool_input = {"file_path": "/tmp/test.txt"}
    return {
        "hook_event_name": "PostToolUse",
        "session_id": session_id,
        "cwd": "/tmp/test-project",
        "permission_mode": "allow",
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_result": tool_result,
    }


def stop_payload(session_id: str = "test-session-001") -> dict[str, Any]:
    """Return a realistic Stop hook payload."""
    return {
        "hook_event_name": "Stop",
        "session_id": session_id,
        "cwd": "/tmp/test-project",
        "permission_mode": "allow",
        "reason": "completed",
    }


def all_fixtures() -> list[dict[str, Any]]:
    """Return one fixture for each supported hook event type."""
    return [
        session_start_payload(),
        pre_tool_use_payload(),
        post_tool_use_payload(),
        stop_payload(),
    ]


def fixture_as_json(payload: dict[str, Any]) -> str:
    """Serialize a fixture payload to JSON string."""
    return json.dumps(payload, ensure_ascii=False)
