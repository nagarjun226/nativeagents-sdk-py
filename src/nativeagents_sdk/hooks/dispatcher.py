"""HookDispatcher: register handlers and dispatch hook events from stdin."""

from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from nativeagents_sdk.schema.events import HookInput

F = TypeVar("F", bound=Callable[..., Any])


class HookDecision:
    """Represents the outcome of a hook handler.

    Use HookDecision.ok() for normal completion.
    Use HookDecision.block(reason) to signal a policy violation.
    """

    def __init__(self, *, should_block: bool = False, reason: str = "") -> None:
        self._should_block = should_block
        self._reason = reason

    @property
    def should_block(self) -> bool:
        """True if Claude Code should be blocked."""
        return self._should_block

    @property
    def reason(self) -> str:
        """Reason for blocking (empty if not blocking)."""
        return self._reason

    @classmethod
    def ok(cls) -> HookDecision:
        """Return a non-blocking decision."""
        return cls(should_block=False)

    @classmethod
    def block(cls, reason: str) -> HookDecision:
        """Return a blocking decision with the given reason.

        Args:
            reason: Human-readable reason printed to stderr.
        """
        return cls(should_block=True, reason=reason)


@dataclass
class HookContext:
    """Context object passed to each hook handler.

    Provides access to the plugin's directories, audit DB, config, and logger.
    The write_audit() convenience method handles connection management.
    """

    plugin_name: str
    plugin_dir: Path
    audit_db: Path
    config: Any  # Config — typed as Any to avoid circular import at module level
    log: logging.Logger
    _conn: sqlite3.Connection | None = field(default=None, repr=False)

    def write_audit(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> str:
        """Write an audit event and return the row_hash.

        Args:
            event_type: Event type string (e.g., "my-plugin.observation").
            payload: Free-form dict payload.
            session_id: Session ID. If None, uses a synthetic placeholder.

        Returns:
            row_hash of the newly inserted row.
        """
        from datetime import datetime

        from nativeagents_sdk.audit.store import open_store, write_event
        from nativeagents_sdk.schema.audit import AuditEvent

        if self._conn is None:
            self._conn = open_store(self.audit_db)

        evt = AuditEvent(
            session_id=session_id or "unknown",
            event_type=event_type,
            plugin_name=self.plugin_name,
            payload=payload,
            timestamp=datetime.now(UTC),
        )
        return write_event(self._conn, evt)

    def close(self) -> None:
        """Close the audit DB connection if open."""
        if self._conn is not None:
            with contextlib.suppress(Exception):  # noqa: BLE001
                self._conn.close()
            self._conn = None


HandlerFn = Callable[[Any, HookContext], HookDecision | None]


class HookDispatcher:
    """Dispatch hook events from stdin to registered Python handlers.

    Usage:
        dispatcher = HookDispatcher(plugin_name="my-plugin")

        @dispatcher.on("PreToolUse")
        def handle_pre(event: PreToolUseInput, ctx: HookContext) -> HookDecision:
            ctx.log.info(f"Tool: {event.tool_name}")
            return HookDecision.ok()

        if __name__ == "__main__":
            dispatcher.run()
    """

    def __init__(self, plugin_name: str) -> None:
        self._plugin_name = plugin_name
        self._handlers: dict[str, HandlerFn] = {}

    def on(self, event_name: str) -> Callable[[F], F]:
        """Decorator to register a handler for a specific hook event.

        Args:
            event_name: Claude Code hook event name (e.g., "PreToolUse").

        Returns:
            Decorator that registers the function and returns it unchanged.
        """

        def decorator(fn: F) -> F:
            cast_fn: HandlerFn = fn
            self._handlers[event_name] = cast_fn
            return fn

        return decorator

    def run(self) -> None:
        """Read hook input from stdin, dispatch to handler, and exit.

        - Exits 0 on success (or when no handler is registered for the event).
        - Exits 0 on handler exception (error is logged).
        - Exits 2 only when handler explicitly returns HookDecision.block().
        """
        from nativeagents_sdk.hooks.runtime import read_hook_input

        event = read_hook_input()
        event_name = event.hook_event_name

        handler = self._handlers.get(event_name)
        if handler is None:
            # No handler registered — silently succeed
            sys.exit(0)

        ctx = self._build_context(event)

        try:
            result = handler(event, ctx)
        except Exception as exc:  # noqa: BLE001
            ctx.log.exception("Unhandled exception in hook handler for %s: %s", event_name, exc)
            result = None
        finally:
            ctx.close()

        if isinstance(result, HookDecision) and result.should_block:
            sys.stderr.write(result.reason + "\n")
            sys.exit(2)

        sys.exit(0)

    def _build_context(self, event: HookInput) -> HookContext:
        """Construct a HookContext for the current invocation."""
        from nativeagents_sdk.config import load_config
        from nativeagents_sdk.paths import audit_db_path, ensure_dir, plugin_dir

        p_dir = plugin_dir(self._plugin_name)
        logs_dir = p_dir / "logs"

        with contextlib.suppress(OSError):  # If we can't create logs dir, use stderr
            ensure_dir(logs_dir)

        log = _get_plugin_logger(self._plugin_name, logs_dir)

        try:
            config = load_config()
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load config: %s; using defaults", exc)
            from nativeagents_sdk.config import Config

            config = Config()

        return HookContext(
            plugin_name=self._plugin_name,
            plugin_dir=p_dir,
            audit_db=audit_db_path(),
            config=config,
            log=log,
        )


def _get_plugin_logger(plugin_name: str, logs_dir: Path) -> logging.Logger:
    """Return a logger that writes to <logs_dir>/hook.log."""
    logger = logging.getLogger(f"nativeagents.plugin.{plugin_name}")
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    # File handler
    log_file = logs_dir / "hook.log"
    try:
        from logging.handlers import RotatingFileHandler

        fh = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(fh)
    except OSError:
        # Fall back to stderr if we can't write to disk
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(sh)

    return logger
