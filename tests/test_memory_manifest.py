"""Tests for memory manifest load, save, rebuild operations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nativeagents_sdk.errors import ManifestError
from nativeagents_sdk.memory.manifest import load_manifest, rebuild_manifest, save_manifest
from nativeagents_sdk.schema.manifest import Manifest, MemoryFile


def make_manifest() -> Manifest:
    now = datetime.now(UTC)
    return Manifest(
        schema_version=1,
        generated_at=now,
        total_token_budget=500,
        files=[
            MemoryFile(
                path="core/user.md",
                name="User Identity",
                description="Core facts",
                category="core",
                token_budget=200,
                write_protected=False,
                created_at=now,
                updated_at=now,
                tags=["identity"],
            )
        ],
    )


def test_save_and_load_roundtrip(isolated_home):
    """save_manifest() + load_manifest() round-trips correctly."""
    from nativeagents_sdk.paths import ensure_dir, memory_dir

    mem_dir = memory_dir()
    ensure_dir(mem_dir)
    path = mem_dir / "manifest.json"

    m = make_manifest()
    save_manifest(path, m)
    loaded = load_manifest(path)

    assert loaded.schema_version == m.schema_version
    assert len(loaded.files) == 1
    assert loaded.files[0].name == "User Identity"
    assert loaded.total_token_budget == 500


def test_load_missing_file(isolated_home):
    """load_manifest() raises ManifestError if file doesn't exist."""
    with pytest.raises(ManifestError):
        load_manifest(Path("/nonexistent/manifest.json"))


def test_load_invalid_json(tmp_path):
    """load_manifest() raises ManifestError on invalid JSON."""
    p = tmp_path / "manifest.json"
    p.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON"):
        load_manifest(p)


def test_load_schema_too_new(tmp_path):
    """load_manifest() raises ManifestError on too-new schema_version."""
    p = tmp_path / "manifest.json"
    data = {
        "schema_version": 999,
        "generated_at": "2026-04-19T00:00:00Z",
        "files": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="schema_version"):
        load_manifest(p)


def test_load_unknown_fields_tolerated(tmp_path):
    """Forward compat: unknown fields are ignored."""
    p = tmp_path / "manifest.json"
    data = {
        "schema_version": 1,
        "generated_at": "2026-04-19T00:00:00Z",
        "files": [],
        "future_field": "some_value",
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    manifest = load_manifest(p)
    assert manifest.schema_version == 1


def test_rebuild_manifest_empty_dir(isolated_home):
    """rebuild_manifest() on empty directory returns empty Manifest."""
    from nativeagents_sdk.paths import ensure_dir, memory_dir

    mem_dir = memory_dir()
    ensure_dir(mem_dir)
    manifest = rebuild_manifest(mem_dir)
    assert manifest.files == []


def test_rebuild_manifest_with_files(isolated_home):
    """rebuild_manifest() scans .md files and builds Manifest."""
    from nativeagents_sdk.paths import ensure_dir, memory_dir

    mem_dir = memory_dir()
    core_dir = mem_dir / "core"
    ensure_dir(core_dir)

    # Create a valid memory file
    (core_dir / "user.md").write_text(
        "---\nname: User Identity\ncategory: core\ntoken_budget: 200\n---\n\n## Content\n",
        encoding="utf-8",
    )

    manifest = rebuild_manifest(mem_dir)
    assert len(manifest.files) == 1
    assert manifest.files[0].name == "User Identity"
    assert manifest.total_token_budget == 200


def test_rebuild_skips_invalid_files(isolated_home):
    """rebuild_manifest() skips files with invalid frontmatter."""
    from nativeagents_sdk.paths import ensure_dir, memory_dir

    mem_dir = memory_dir()
    ensure_dir(mem_dir)

    # Valid file
    (mem_dir / "valid.md").write_text(
        "---\nname: Valid\ntoken_budget: 100\n---\nbody\n",
        encoding="utf-8",
    )
    # Invalid file (no frontmatter)
    (mem_dir / "invalid.md").write_text("# No frontmatter\n", encoding="utf-8")

    manifest = rebuild_manifest(mem_dir)
    assert len(manifest.files) == 1
    assert manifest.files[0].name == "Valid"


def test_save_manifest_atomic(isolated_home):
    """save_manifest() writes atomically — no .tmp files left behind."""
    from nativeagents_sdk.paths import ensure_dir, memory_dir

    mem_dir = memory_dir()
    ensure_dir(mem_dir)
    path = mem_dir / "manifest.json"
    save_manifest(path, make_manifest())
    assert path.exists()
    tmp_files = list(path.parent.glob("*.tmp*"))
    assert tmp_files == []
