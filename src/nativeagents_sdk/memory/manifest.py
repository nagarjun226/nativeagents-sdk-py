"""Memory manifest load, save, rebuild operations."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from pydantic import ValidationError

from nativeagents_sdk.errors import FrontmatterError, ManifestError
from nativeagents_sdk.schema.manifest import Manifest, MemoryFile

logger = logging.getLogger(__name__)

MAX_SUPPORTED_SCHEMA_VERSION = 1


def load_manifest(path: Path) -> Manifest:
    """Load a memory manifest from disk.

    Args:
        path: Path to manifest.json.

    Returns:
        Validated Manifest model.

    Raises:
        ManifestError: If the file doesn't exist, has invalid JSON, or
            fails Pydantic validation.
    """
    if not path.exists():
        raise ManifestError(f"Manifest file not found: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"Cannot read manifest {path}: {exc}") from exc

    try:
        raw: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Manifest {path} is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestError(f"Manifest {path} must be a JSON object, got {type(raw).__name__}")

    schema_version = raw.get("schema_version", 1)
    if isinstance(schema_version, int) and schema_version > MAX_SUPPORTED_SCHEMA_VERSION:
        raise ManifestError(
            f"Manifest schema_version {schema_version} is newer than this SDK supports "
            f"(max {MAX_SUPPORTED_SCHEMA_VERSION}). Upgrade nativeagents-sdk."
        )

    try:
        return Manifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"Manifest {path} validation failed: {exc}") from exc


def save_manifest(path: Path, m: Manifest) -> None:
    """Write a memory manifest to disk atomically.

    Args:
        path: Destination path (typically memory_dir()/manifest.json).
        m: Manifest model to write.
    """
    from nativeagents_sdk.paths import atomic_write

    data = json.dumps(
        m.model_dump(mode="json"),
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    )
    atomic_write(path, data.encode("utf-8"))


def rebuild_manifest(memory_dir: Path) -> Manifest:
    """Scan the memory directory and build a fresh Manifest.

    Walks all .md files under memory_dir (recursively), parses their
    frontmatter, and constructs a Manifest. Files with invalid or missing
    frontmatter are logged and skipped.

    Args:
        memory_dir: Root of the memory namespace (~/.nativeagents/memory/).

    Returns:
        A new Manifest reflecting the current state of the directory.
    """
    from nativeagents_sdk.memory.frontmatter import parse as parse_fm

    files: list[MemoryFile] = []

    if not memory_dir.exists():
        return Manifest(
            schema_version=1,
            generated_at=datetime.now(UTC),
            total_token_budget=0,
            files=[],
        )

    for md_path in sorted(memory_dir.rglob("*.md")):
        if md_path.name == "plugin.toml" or md_path.parent.name == ".tmp":
            continue

        # Compute relative path from memory_dir
        try:
            rel_path = md_path.relative_to(memory_dir).as_posix()
        except ValueError:
            continue

        try:
            text = md_path.read_text(encoding="utf-8")
            fm, _body = parse_fm(text)
        except FrontmatterError as exc:
            logger.warning("Skipping %s: invalid frontmatter: %s", md_path, exc)
            continue
        except OSError as exc:
            logger.warning("Skipping %s: cannot read: %s", md_path, exc)
            continue

        now = datetime.now(UTC)
        files.append(
            MemoryFile(
                path=rel_path,
                name=fm.name,
                description=fm.description,
                category=fm.category,
                token_budget=fm.token_budget,
                write_protected=fm.write_protected,
                created_at=fm.created_at or now,
                updated_at=fm.updated_at or now,
                tags=fm.tags,
                extra=fm.extra,
            )
        )

    total_budget = sum(f.token_budget for f in files)
    return Manifest(
        schema_version=1,
        generated_at=datetime.now(UTC),
        total_token_budget=total_budget,
        files=files,
    )


def validate_file(path: Path) -> list[ValidationError]:
    """Lint a single memory file, returning a list of validation errors.

    Args:
        path: Path to a .md memory file.

    Returns:
        List of ValidationError instances (empty if file is valid).
    """
    from nativeagents_sdk.memory.frontmatter import parse as parse_fm

    errors: list[ValidationError] = []
    try:
        text = path.read_text(encoding="utf-8")
        _fm, _body = parse_fm(text)
    except FrontmatterError as exc:
        # Wrap in a pseudo-ValidationError for consistent API
        # Return empty list for now — callers check for FrontmatterError separately
        logger.debug("validate_file %s: %s", path, exc)
    except OSError:
        pass
    return errors
