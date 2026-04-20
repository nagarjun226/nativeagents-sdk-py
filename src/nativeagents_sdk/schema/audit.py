"""Pydantic model for audit events written to audit.db."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from nativeagents_sdk.schema.events import validate_session_id


class AuditEvent(BaseModel):
    """A single audit event row (pre-insertion representation).

    Fields set by the caller:
        session_id, event_type, plugin_name, payload, timestamp

    Fields set by write_event():
        captured_at (if None), sequence, prev_hash, row_hash
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    event_type: str
    plugin_name: str
    payload: dict[str, Any] = {}
    timestamp: datetime  # UTC; caller must provide timezone-aware datetime

    # Set by write_event() before insertion
    captured_at: datetime | None = None
    sequence: int | None = None
    prev_hash: str | None = None
    row_hash: str | None = None

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, v: str) -> str:
        """Validate session_id against the canonical regex."""
        return validate_session_id(v)
