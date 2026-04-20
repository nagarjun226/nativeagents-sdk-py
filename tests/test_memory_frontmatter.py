"""Tests for memory file frontmatter parsing and rendering."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nativeagents_sdk.errors import FrontmatterError
from nativeagents_sdk.memory.frontmatter import parse, render
from nativeagents_sdk.schema.frontmatter import Frontmatter

SAMPLE_FILE = """\
---
name: My Memory File
description: A test file
category: working
token_budget: 200
write_protected: false
created_at: 2026-04-19T00:00:00Z
updated_at: 2026-04-19T12:00:00Z
tags:
  - test
  - memory
---

## Content

Some body text.
"""


def test_parse_valid_frontmatter():
    """parse() extracts Frontmatter and body from valid file."""
    fm, body = parse(SAMPLE_FILE)
    assert fm.name == "My Memory File"
    assert fm.description == "A test file"
    assert fm.category == "working"
    assert fm.token_budget == 200
    assert fm.write_protected is False
    assert "test" in fm.tags
    assert "memory" in fm.tags
    assert "## Content" in body


def test_parse_missing_frontmatter():
    """parse() raises FrontmatterError when frontmatter is absent."""
    with pytest.raises(FrontmatterError):
        parse("# Just a markdown file\nNo frontmatter here.\n")


def test_parse_invalid_yaml():
    """parse() raises FrontmatterError on invalid YAML."""
    content = "---\nname: [unclosed bracket\n---\nbody\n"
    with pytest.raises(FrontmatterError):
        parse(content)


def test_render_basic():
    """render() produces a file with '---' delimiters."""
    fm = Frontmatter(name="Test File")
    body = "## Test\n\nContent.\n"
    result = render(fm, body)
    assert result.startswith("---\n")
    assert "---\n" in result[4:]
    assert "Test File" in result
    assert "## Test" in result


def test_render_parse_roundtrip():
    """render() + parse() is a round-trip."""
    fm = Frontmatter(
        name="Round Trip",
        description="Testing",
        category="core",
        token_budget=500,
        write_protected=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 4, 1, tzinfo=UTC),
        tags=["tag1", "tag2"],
    )
    body = "## Round Trip\n\nSome text.\n"
    rendered = render(fm, body)
    fm2, body2 = parse(rendered)

    assert fm2.name == fm.name
    assert fm2.description == fm.description
    assert fm2.category == fm.category
    assert fm2.token_budget == fm.token_budget
    assert fm2.write_protected == fm.write_protected
    assert sorted(fm2.tags) == sorted(fm.tags)
    assert "## Round Trip" in body2


def test_parse_minimal_frontmatter():
    """parse() works with only the required 'name' field."""
    content = "---\nname: Minimal\n---\nbody\n"
    fm, body = parse(content)
    assert fm.name == "Minimal"
    assert fm.token_budget == 0
    assert fm.tags == []


def test_parse_extra_fields_preserved():
    """Unknown frontmatter fields are collected in extra."""
    content = "---\nname: Test\nfuture_field: some_value\n---\nbody\n"
    fm, _ = parse(content)
    assert fm.extra.get("future_field") == "some_value"
