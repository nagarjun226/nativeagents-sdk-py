"""Hook dispatcher and runtime utilities for the Native Agents SDK."""

from nativeagents_sdk.hooks.dispatcher import HookContext, HookDecision, HookDispatcher
from nativeagents_sdk.hooks.runtime import block, fail, ok, read_hook_input
from nativeagents_sdk.schema.events import (
    HookInput,
    NotificationInput,
    PostCompactInput,
    PostToolUseInput,
    PreCompactInput,
    PreToolUseInput,
    SessionEndInput,
    SessionStartInput,
    StopInput,
    SubagentStopInput,
    UserPromptSubmitInput,
)

__all__ = [
    # Dispatcher
    "HookDispatcher",
    "HookContext",
    "HookDecision",
    # Runtime
    "read_hook_input",
    "ok",
    "fail",
    "block",
    # Event models
    "HookInput",
    "SessionStartInput",
    "UserPromptSubmitInput",
    "PreToolUseInput",
    "PostToolUseInput",
    "StopInput",
    "SubagentStopInput",
    "NotificationInput",
    "PreCompactInput",
    "PostCompactInput",
    "SessionEndInput",
]
