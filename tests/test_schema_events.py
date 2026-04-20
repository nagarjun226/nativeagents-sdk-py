"""Tests for schema/events.py hook event models."""

import pytest
from pydantic import ValidationError

from nativeagents_sdk.schema.events import (
    HOOK_INPUT_MODELS,
    HookEventType,
    HookInput,
    PostToolUseInput,
    PreToolUseInput,
    SessionStartInput,
    StopInput,
    validate_session_id,
)


def test_hook_event_type_values():
    """HookEventType enum has all expected values."""
    expected = {
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "SubagentStop",
        "Stop",
        "Notification",
        "PreCompact",
        "PostCompact",
        "SessionEnd",
    }
    actual = {e.value for e in HookEventType}
    assert actual == expected


def test_validate_session_id_valid():
    valid_ids = ["abc123", "test-session-001", "Session_ID_123", "a" * 128]
    for sid in valid_ids:
        assert validate_session_id(sid) == sid


def test_validate_session_id_invalid():
    invalid_ids = ["", "a" * 129, "has space", "has/slash", "has.dot"]
    for sid in invalid_ids:
        with pytest.raises(ValueError):
            validate_session_id(sid)


def test_session_start_input():
    data = {
        "hook_event_name": "SessionStart",
        "session_id": "abc123",
        "cwd": "/tmp",
        "permission_mode": "allow",
    }
    model = SessionStartInput.model_validate(data)
    assert model.session_id == "abc123"
    assert model.hook_event_name == "SessionStart"


def test_pre_tool_use_input():
    data = {
        "hook_event_name": "PreToolUse",
        "session_id": "abc123",
        "cwd": "/tmp",
        "permission_mode": "allow",
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.txt"},
    }
    model = PreToolUseInput.model_validate(data)
    assert model.tool_name == "Read"
    assert model.tool_input == {"file_path": "/tmp/test.txt"}


def test_post_tool_use_input():
    data = {
        "hook_event_name": "PostToolUse",
        "session_id": "abc123",
        "cwd": "/tmp",
        "permission_mode": "allow",
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/out.txt"},
        "tool_result": "written",
    }
    model = PostToolUseInput.model_validate(data)
    assert model.tool_result == "written"


def test_stop_input():
    data = {
        "hook_event_name": "Stop",
        "session_id": "abc123",
        "cwd": "/tmp",
        "permission_mode": "allow",
        "reason": "done",
    }
    model = StopInput.model_validate(data)
    assert model.reason == "done"


def test_hook_input_models_mapping():
    """HOOK_INPUT_MODELS maps all event names to correct model classes."""
    assert HOOK_INPUT_MODELS["PreToolUse"] is PreToolUseInput
    assert HOOK_INPUT_MODELS["PostToolUse"] is PostToolUseInput
    assert HOOK_INPUT_MODELS["SessionStart"] is SessionStartInput
    assert HOOK_INPUT_MODELS["Stop"] is StopInput


def test_hook_input_allows_extra_fields():
    """HookInput models tolerate unknown fields (forward compat)."""
    data = {
        "hook_event_name": "SessionStart",
        "session_id": "abc123",
        "cwd": "/tmp",
        "permission_mode": "allow",
        "future_field": "some_value",
    }
    model = HookInput.model_validate(data)
    assert model.session_id == "abc123"


def test_invalid_session_id_in_model():
    """Model validation fails for invalid session_id."""
    data = {
        "hook_event_name": "SessionStart",
        "session_id": "has/invalid/chars",
        "cwd": "/tmp",
    }
    with pytest.raises(ValidationError):
        SessionStartInput.model_validate(data)
