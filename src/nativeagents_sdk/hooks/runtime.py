"""Hook runtime utilities: read stdin, exit-code helpers.

Exit code contract (matches Claude Code's expectations):
  0 — hook handled successfully, OR hook errored (errors are logged, not propagated)
  2 — explicit block: Claude Code will refuse to proceed
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from nativeagents_sdk.schema.events import HOOK_INPUT_MODELS, HookInput

logger = logging.getLogger(__name__)


def read_hook_input() -> HookInput:
    """Read and parse a hook event from stdin.

    Prefers HOOK_EVENT_NAME environment variable for the event type;
    falls back to hook_event_name in the JSON payload.

    Returns:
        A typed HookInput subclass instance.

    Raises:
        SystemExit(1): If stdin is not valid JSON or the event type is
            unrecognized and we cannot fall back gracefully.
    """
    raw_text = sys.stdin.read()

    try:
        raw: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse hook input from stdin: %s", exc)
        sys.exit(1)

    if not isinstance(raw, dict):
        logger.error("Hook input is not a JSON object, got %s", type(raw).__name__)
        sys.exit(1)

    # Prefer env var, fall back to payload field
    event_name: str | None = os.environ.get("HOOK_EVENT_NAME") or raw.get("hook_event_name")

    if not event_name:
        logger.error(
            "Cannot determine hook event name (no HOOK_EVENT_NAME env or hook_event_name field)"
        )
        sys.exit(1)

    # Ensure hook_event_name is set in the dict for Pydantic
    raw["hook_event_name"] = event_name

    model_class = HOOK_INPUT_MODELS.get(event_name, HookInput)

    try:
        return model_class.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Hook input validation failed for %s: %s; using base HookInput",
            event_name,
            exc,
        )
        return HookInput.model_validate(raw)


def ok() -> None:
    """Exit 0 — hook succeeded."""
    sys.exit(0)


def fail(msg: str) -> None:
    """Log an error and exit 0 — hooks NEVER block Claude Code due to plugin errors.

    Args:
        msg: Human-readable failure message (logged, not sent to Claude Code).
    """
    logger.error("Hook failed (non-blocking): %s", msg)
    sys.exit(0)


def block(reason: str) -> None:
    """Print reason to stderr and exit 2 — Claude Code will refuse to proceed.

    Use only for deliberate policy enforcement. Never for error handling.

    Args:
        reason: Human-readable reason for blocking (printed to stderr).
    """
    sys.stderr.write(reason + "\n")
    sys.exit(2)
