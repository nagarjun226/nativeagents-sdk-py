"""Pydantic models for Claude Code hook events.

These models represent the JSON payloads that Claude Code writes to stdin
when a hook fires. The shape is based on the canonical agentaudit-cc schema.

Preferred: Claude Code sets HOOK_EVENT_NAME env var.
Fallback: `hook_event_name` field in the JSON payload.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


def validate_session_id(value: str) -> str:
    """Validate session ID format, raising ValueError if invalid."""
    if not _SESSION_ID_RE.match(value):
        raise ValueError(f"Invalid session_id {value!r}. Must match ^[a-zA-Z0-9_-]{{{{1,128}}}}$")
    return value


class HookEventType(StrEnum):
    """Canonical Claude Code hook event names (as of 2026-04)."""

    SessionStart = "SessionStart"
    UserPromptSubmit = "UserPromptSubmit"
    PreToolUse = "PreToolUse"
    PostToolUse = "PostToolUse"
    SubagentStop = "SubagentStop"
    Stop = "Stop"
    Notification = "Notification"
    PreCompact = "PreCompact"
    PostCompact = "PostCompact"
    SessionEnd = "SessionEnd"


class HookInput(BaseModel):
    """Base model shared by all Claude Code hook events.

    Claude Code always includes these fields in every hook payload.
    """

    model_config = ConfigDict(extra="allow")

    hook_event_name: str
    session_id: str
    cwd: str
    permission_mode: str = "allow"
    transcript_path: str | None = None

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, v: str) -> str:
        return validate_session_id(v)


class SessionStartInput(HookInput):
    """Hook payload for SessionStart events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "SessionStart"


class UserPromptSubmitInput(HookInput):
    """Hook payload for UserPromptSubmit events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "UserPromptSubmit"
    user_prompt: str = ""


class PreToolUseInput(HookInput):
    """Hook payload for PreToolUse events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "PreToolUse"
    tool_name: str = ""
    tool_input: dict[str, Any] = {}


class PostToolUseInput(HookInput):
    """Hook payload for PostToolUse events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "PostToolUse"
    tool_name: str = ""
    tool_input: dict[str, Any] = {}
    tool_result: Any = None


class StopInput(HookInput):
    """Hook payload for Stop events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "Stop"
    reason: str = ""
    stop_hook_active: bool = False


class SubagentStopInput(HookInput):
    """Hook payload for SubagentStop events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "SubagentStop"
    reason: str = ""


class NotificationInput(HookInput):
    """Hook payload for Notification events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "Notification"
    message: str = ""


class PreCompactInput(HookInput):
    """Hook payload for PreCompact events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "PreCompact"
    trigger: str = ""


class PostCompactInput(HookInput):
    """Hook payload for PostCompact events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "PostCompact"


class SessionEndInput(HookInput):
    """Hook payload for SessionEnd events."""

    model_config = ConfigDict(extra="allow")

    hook_event_name: str = "SessionEnd"


# Mapping from event name string to the corresponding Pydantic model class.
# Use this to parse raw JSON into the correct typed model.
HOOK_INPUT_MODELS: dict[str, type[HookInput]] = {
    "SessionStart": SessionStartInput,
    "UserPromptSubmit": UserPromptSubmitInput,
    "PreToolUse": PreToolUseInput,
    "PostToolUse": PostToolUseInput,
    "Stop": StopInput,
    "SubagentStop": SubagentStopInput,
    "Notification": NotificationInput,
    "PreCompact": PreCompactInput,
    "PostCompact": PostCompactInput,
    "SessionEnd": SessionEndInput,
}
