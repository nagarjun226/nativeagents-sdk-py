"""YAML frontmatter parser and renderer for memory files.

Memory files are Markdown with YAML frontmatter delimited by '---' lines.
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from pydantic import ValidationError

from nativeagents_sdk.errors import FrontmatterError
from nativeagents_sdk.schema.frontmatter import Frontmatter

# Matches: '---\n<yaml>\n---\n<body>'
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)

# Known frontmatter fields (all others go into extra)
_KNOWN_FIELDS = frozenset(
    [
        "name",
        "description",
        "category",
        "token_budget",
        "write_protected",
        "created_at",
        "updated_at",
        "tags",
    ]
)


def parse(text: str) -> tuple[Frontmatter, str]:
    """Parse YAML frontmatter from a memory file.

    Args:
        text: Full file content including frontmatter.

    Returns:
        Tuple of (Frontmatter model, body string without frontmatter).

    Raises:
        FrontmatterError: If frontmatter is missing, invalid YAML, or fails
            Pydantic validation.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise FrontmatterError(
            "Memory file does not have valid YAML frontmatter. "
            "Expected '---\\n<yaml>\\n---\\n' at the start of the file."
        )

    yaml_text = m.group(1)
    body = m.group(2)

    try:
        raw: Any = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"Invalid YAML in frontmatter: {exc}") from exc

    if raw is None:
        raw = {}

    if not isinstance(raw, dict):
        raise FrontmatterError(f"Frontmatter must be a YAML mapping, got {type(raw).__name__}")

    # Separate known fields from extras
    known: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _KNOWN_FIELDS:
            known[k] = v
        elif k != "extra":
            extra[k] = v
        else:
            # If 'extra' key is explicitly present, merge it
            if isinstance(v, dict):
                extra.update(v)

    known["extra"] = extra

    try:
        fm = Frontmatter.model_validate(known)
    except ValidationError as exc:
        raise FrontmatterError(f"Frontmatter validation failed: {exc}") from exc

    return fm, body


def render(fm: Frontmatter, body: str) -> str:
    """Render a Frontmatter model back to a memory file string.

    Args:
        fm: Frontmatter model.
        body: Markdown body content (without frontmatter).

    Returns:
        Complete file content with '---\\n<yaml>\\n---\\n<body>'.
    """
    data: dict[str, Any] = {}
    data["name"] = fm.name
    if fm.description:
        data["description"] = fm.description
    data["category"] = fm.category
    data["token_budget"] = fm.token_budget
    data["write_protected"] = fm.write_protected
    if fm.created_at is not None:
        data["created_at"] = fm.created_at
    if fm.updated_at is not None:
        data["updated_at"] = fm.updated_at
    if fm.tags:
        data["tags"] = fm.tags
    # Merge extra fields at top level (round-trip preservation)
    for k, v in fm.extra.items():
        if k not in data:
            data[k] = v

    yaml_text = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()

    return f"---\n{yaml_text}\n---\n{body}"
