"""Pydantic model for memory file YAML frontmatter."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict


class Frontmatter(BaseModel):
    """YAML frontmatter for a memory file.

    Maps 1:1 to the MemoryFile model fields (minus path which comes from
    filesystem location). Unknown keys are collected in `extra`.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str = ""
    category: str = "working"
    token_budget: int = 0
    write_protected: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: list[str] = []
    extra: dict[str, Any] = {}
