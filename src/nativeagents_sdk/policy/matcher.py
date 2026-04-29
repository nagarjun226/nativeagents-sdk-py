"""Policy DSL matcher primitives.

Four match modes supported in ``input_matches`` and ``not_matches`` rule
sections:

``contains`` — substring present in the field value::

    command:
      - contains: "rm -rf"
        why: "destructive rm"

``regex`` — Python ``re.search`` with ``re.MULTILINE``::

    command:
      - regex: 'rm\\s+(?:-[rRf]+\\s+)+'
        why: "rm with recursive/force flags"
      - regex: 'some.pattern'
        dotall: true   # adds re.DOTALL

``glob`` — ``pathlib.PurePosixPath.match`` + ``fnmatch`` fallback::

    file_path:
      - glob: "**/.env"
      - glob: "**/*.pem"

``shell`` — ``shlex``-parsed argv inspection::

    command:
      - shell:
          program: rm
          args_contain: ["-r", "-rf", "-R"]
        why: "rm with recursive flag"

Each spec dict should have exactly one of the four mode keys.  An optional
``why`` key provides a human-readable reason string on match.

Bare strings (backward-compat) are treated as ``contains``::

    command:
      - "rm -rf"
"""

from __future__ import annotations

import contextlib
import fnmatch
import logging
import re
import shlex
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

logger = logging.getLogger(__name__)


class MatchMode(StrEnum):
    """Supported match modes for policy rule specs."""

    CONTAINS = "contains"
    REGEX = "regex"
    GLOB = "glob"
    SHELL = "shell"


class Matcher:
    """Stateless matcher for policy DSL specs.

    All methods are static — instantiation is not required.
    """

    @staticmethod
    def match_spec(spec: dict[str, Any], field: str, value: str) -> str | None:
        """Evaluate one match-spec dict against a field value.

        Args:
            spec: Dict with one of the four mode keys (``contains``,
                ``regex``, ``glob``, ``shell``) plus an optional ``why``.
            field: Field name (used in fallback reason strings).
            value: The string value to test.

        Returns:
            A human-readable reason string on match; ``None`` otherwise.
        """
        if MatchMode.CONTAINS in spec:
            substr = str(spec[MatchMode.CONTAINS])
            if substr in value:
                return spec.get("why") or f"{field} contains {substr!r}"

        if MatchMode.REGEX in spec:
            pat = spec[MatchMode.REGEX]
            flags = re.MULTILINE
            if spec.get("dotall"):
                flags |= re.DOTALL
            try:
                if re.search(pat, value, flags):
                    return spec.get("why") or f"{field} matches pattern"
            except re.error as exc:
                logger.warning("Invalid regex in policy spec %r: %s", pat, exc)

        if MatchMode.GLOB in spec:
            pat = spec[MatchMode.GLOB]
            matched = False
            with contextlib.suppress(Exception):
                matched = PurePosixPath(value).match(pat)
            if not matched:
                matched = fnmatch.fnmatch(value, pat)
            if matched:
                return spec.get("why") or f"{field} matches glob {pat!r}"

        if MatchMode.SHELL in spec:
            shell_spec = spec[MatchMode.SHELL]
            try:
                parts = shlex.split(value)
            except ValueError:
                return None

            prog: str | None = shell_spec.get("program")
            if prog:
                prog_found = any(p == prog or p.endswith("/" + prog) for p in parts)
                if not prog_found:
                    return None

            args_contain: list[str] = shell_spec.get("args_contain", [])
            if args_contain and not any(a in parts for a in args_contain):
                return None

            return spec.get("why") or (
                f"{field}: shell {prog!r} with flags {args_contain}"
                if prog
                else f"{field}: shell args {args_contain}"
            )

        return None

    @staticmethod
    def match_tool_name(pattern: str | list[Any], tool_name: str) -> bool:
        """Return True if ``tool_name`` satisfies ``pattern``.

        ``pattern`` may be:
        - A string: exact equality, or fnmatch glob if it contains ``*``/``?``.
        - A list: any element may match (recursive).
        """
        if isinstance(pattern, str):
            if "*" in pattern or "?" in pattern:
                return fnmatch.fnmatch(tool_name, pattern)
            return pattern == tool_name
        if isinstance(pattern, list):
            return any(Matcher.match_tool_name(item, tool_name) for item in pattern)
        return False

    @staticmethod
    def match_inputs(
        patterns: dict[str, list[Any]],
        tool_input: dict[str, Any],
    ) -> str | None:
        """Check ``tool_input`` against a patterns dict.

        Args:
            patterns: Maps field name → list of specs.  Each spec is either
                a bare string (backward-compat substring contains) or a dict
                with one of the four mode keys.
            tool_input: The tool's input dict.

        Returns:
            Reason string for the first match, or ``None``.
        """
        for field, match_list in patterns.items():
            value = str(tool_input.get(field, ""))
            for spec in match_list:
                if isinstance(spec, str):
                    if spec in value:
                        return f"{field} contains {spec!r}"
                elif isinstance(spec, dict):
                    reason = Matcher.match_spec(spec, field, value)
                    if reason:
                        return reason
        return None
