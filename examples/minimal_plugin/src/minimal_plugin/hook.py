"""Hook handlers for minimal-plugin.

Demonstrates PreToolUse + PostToolUse with duration tracking via the SDK.
"""

from __future__ import annotations

import sys
import time
from typing import Any

from nativeagents_sdk.hooks import HookDecision, HookDispatcher, PostToolUseInput, PreToolUseInput

dispatcher = HookDispatcher(plugin_name="minimal-plugin")

_start_times: dict[str, float] = {}


@dispatcher.on("PreToolUse")
def on_pre_tool_use(event: PreToolUseInput, ctx: Any) -> HookDecision:
    """Record start time and write a pre-use audit entry."""
    _start_times[event.session_id] = time.monotonic()
    sys.stderr.write(f"[minimal-plugin] pre: {event.tool_name}\n")

    ctx.write_audit(
        event_type="minimal-plugin.pre_tool_use",
        payload={"tool_name": event.tool_name, "input_keys": list(event.tool_input.keys())},
        session_id=event.session_id,
    )
    return HookDecision.ok()


@dispatcher.on("PostToolUse")
def on_post_tool_use(event: PostToolUseInput, ctx: Any) -> HookDecision:
    """Compute duration and write a post-use audit entry."""
    elapsed = time.monotonic() - _start_times.pop(event.session_id, time.monotonic())
    duration_ms = round(elapsed * 1000)
    sys.stderr.write(f"[minimal-plugin] post: {event.tool_name} ({duration_ms} ms)\n")

    ctx.write_audit(
        event_type="minimal-plugin.post_tool_use",
        payload={"tool_name": event.tool_name, "duration_ms": duration_ms},
        session_id=event.session_id,
    )
    return HookDecision.ok()


if __name__ == "__main__":
    dispatcher.run()
