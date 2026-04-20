"""Pydantic models for the memory manifest (manifest.json)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict


class MemoryFile(BaseModel):
    """A single entry in the memory manifest's files array."""

    model_config = ConfigDict(extra="ignore")

    path: str  # relative to ~/.nativeagents/memory/
    name: str
    description: str = ""
    category: str = "working"
    token_budget: int = 0
    write_protected: bool = False
    created_at: datetime
    updated_at: datetime
    tags: list[str] = []
    extra: dict[str, Any] = {}


class Manifest(BaseModel):
    """Top-level memory manifest model.

    Corresponds to ~/.nativeagents/memory/manifest.json.
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    generated_at: datetime
    total_token_budget: int = 0
    files: list[MemoryFile] = []
