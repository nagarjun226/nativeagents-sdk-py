"""Tests for nativeagents_sdk.policy (Matcher + MatchMode)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nativeagents_sdk.policy import Matcher, MatchMode

# ---------------------------------------------------------------------------
# MatchMode enum
# ---------------------------------------------------------------------------


def test_match_mode_values() -> None:
    assert MatchMode.CONTAINS == "contains"
    assert MatchMode.REGEX == "regex"
    assert MatchMode.GLOB == "glob"
    assert MatchMode.SHELL == "shell"


# ---------------------------------------------------------------------------
# Matcher.match_spec — contains mode
# ---------------------------------------------------------------------------


def test_contains_match() -> None:
    spec = {"contains": "rm -rf"}
    assert Matcher.match_spec(spec, "command", "sudo rm -rf /tmp") is not None


def test_contains_no_match() -> None:
    spec = {"contains": "rm -rf"}
    assert Matcher.match_spec(spec, "command", "ls -la") is None


def test_contains_custom_why() -> None:
    spec = {"contains": "secret", "why": "found secret token"}
    reason = Matcher.match_spec(spec, "text", "my secret value")
    assert reason == "found secret token"


def test_contains_default_reason() -> None:
    spec = {"contains": "foo"}
    reason = Matcher.match_spec(spec, "field", "foobar")
    assert reason is not None
    assert "foo" in reason
    assert "field" in reason


def test_contains_empty_string_matches_everything() -> None:
    spec = {"contains": ""}
    assert Matcher.match_spec(spec, "f", "anything") is not None


# ---------------------------------------------------------------------------
# Matcher.match_spec — regex mode
# ---------------------------------------------------------------------------


def test_regex_match() -> None:
    spec = {"regex": r"rm\s+-rf"}
    assert Matcher.match_spec(spec, "cmd", "rm -rf /") is not None


def test_regex_no_match() -> None:
    spec = {"regex": r"rm\s+-rf"}
    assert Matcher.match_spec(spec, "cmd", "ls -la") is None


def test_regex_multiline_default() -> None:
    spec = {"regex": r"^secret$"}
    assert Matcher.match_spec(spec, "text", "preamble\nsecret\npostamble") is not None


def test_regex_dotall_flag() -> None:
    spec = {"regex": r"start.+end", "dotall": True}
    assert Matcher.match_spec(spec, "text", "start\nmiddle\nend") is not None


def test_regex_dotall_off_no_match() -> None:
    spec = {"regex": r"start.+end"}
    assert Matcher.match_spec(spec, "text", "start\nmiddle\nend") is None


def test_regex_invalid_pattern_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    spec = {"regex": "[invalid("}
    result = Matcher.match_spec(spec, "field", "value")
    assert result is None


def test_regex_custom_why() -> None:
    spec = {"regex": r"\d{4}", "why": "contains year"}
    reason = Matcher.match_spec(spec, "text", "year 2026")
    assert reason == "contains year"


# ---------------------------------------------------------------------------
# Matcher.match_spec — glob mode
# ---------------------------------------------------------------------------


def test_glob_posix_path_match() -> None:
    spec = {"glob": "**/.env"}
    assert Matcher.match_spec(spec, "path", "/home/user/project/.env") is not None


def test_glob_pem_extension() -> None:
    spec = {"glob": "**/*.pem"}
    assert Matcher.match_spec(spec, "path", "/etc/ssl/cert.pem") is not None


def test_glob_no_match() -> None:
    spec = {"glob": "**/.env"}
    assert Matcher.match_spec(spec, "path", "/home/user/project/main.py") is None


def test_glob_fnmatch_fallback() -> None:
    spec = {"glob": "*.txt"}
    assert Matcher.match_spec(spec, "file", "readme.txt") is not None


def test_glob_custom_why() -> None:
    spec = {"glob": "**/*.key", "why": "private key file"}
    reason = Matcher.match_spec(spec, "path", "/home/user/.ssh/id_rsa.key")
    assert reason == "private key file"


# ---------------------------------------------------------------------------
# Matcher.match_spec — shell mode
# ---------------------------------------------------------------------------


def test_shell_program_and_args() -> None:
    spec = {"shell": {"program": "rm", "args_contain": ["-rf", "-r"]}}
    assert Matcher.match_spec(spec, "cmd", "rm -rf /tmp") is not None


def test_shell_program_only() -> None:
    spec = {"shell": {"program": "curl"}}
    assert Matcher.match_spec(spec, "cmd", "curl https://example.com") is not None


def test_shell_program_not_found() -> None:
    spec = {"shell": {"program": "rm", "args_contain": ["-rf"]}}
    assert Matcher.match_spec(spec, "cmd", "ls -la") is None


def test_shell_args_missing() -> None:
    spec = {"shell": {"program": "rm", "args_contain": ["-rf"]}}
    assert Matcher.match_spec(spec, "cmd", "rm /tmp/file") is None


def test_shell_path_prefixed_program() -> None:
    spec = {"shell": {"program": "rm", "args_contain": ["-r"]}}
    assert Matcher.match_spec(spec, "cmd", "/bin/rm -r /tmp") is not None


def test_shell_unparseable_returns_none() -> None:
    spec = {"shell": {"program": "rm"}}
    # Unmatched quote makes shlex.split raise
    assert Matcher.match_spec(spec, "cmd", "rm 'unclosed") is None


def test_shell_custom_why() -> None:
    spec = {"shell": {"program": "git", "args_contain": ["push", "--force"]}, "why": "force push"}
    reason = Matcher.match_spec(spec, "cmd", "git push --force origin main")
    assert reason == "force push"


# ---------------------------------------------------------------------------
# Matcher.match_tool_name
# ---------------------------------------------------------------------------


def test_tool_name_exact_match() -> None:
    assert Matcher.match_tool_name("Bash", "Bash") is True


def test_tool_name_exact_no_match() -> None:
    assert Matcher.match_tool_name("Bash", "Write") is False


def test_tool_name_glob_wildcard() -> None:
    assert Matcher.match_tool_name("mcp__*__delete_*", "mcp__linear__delete_issue") is True


def test_tool_name_glob_no_match() -> None:
    assert Matcher.match_tool_name("mcp__*__delete_*", "mcp__linear__create_issue") is False


def test_tool_name_list_any_match() -> None:
    assert Matcher.match_tool_name(["Bash", "Write", "Edit"], "Write") is True


def test_tool_name_list_no_match() -> None:
    assert Matcher.match_tool_name(["Bash", "Write"], "Read") is False


def test_tool_name_unknown_type_returns_false() -> None:
    assert Matcher.match_tool_name(42, "Bash") is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Matcher.match_inputs
# ---------------------------------------------------------------------------


def test_match_inputs_bare_string_contains() -> None:
    patterns = {"command": ["rm -rf"]}
    assert Matcher.match_inputs(patterns, {"command": "sudo rm -rf /"}) is not None


def test_match_inputs_dict_spec() -> None:
    patterns = {"command": [{"regex": r"rm\s+-rf"}]}
    assert Matcher.match_inputs(patterns, {"command": "rm -rf /"}) is not None


def test_match_inputs_no_match() -> None:
    patterns = {"command": ["rm -rf"]}
    assert Matcher.match_inputs(patterns, {"command": "ls -la"}) is None


def test_match_inputs_missing_field_treated_as_empty() -> None:
    patterns = {"file_path": [{"glob": "**/.env"}]}
    assert Matcher.match_inputs(patterns, {}) is None


def test_match_inputs_first_match_wins() -> None:
    patterns = {"command": ["ls", "rm"]}
    reason = Matcher.match_inputs(patterns, {"command": "ls"})
    assert reason is not None and "ls" in reason


def test_match_inputs_multiple_fields() -> None:
    patterns = {"command": ["safe"], "file_path": [{"glob": "**/.env"}]}
    result = Matcher.match_inputs(patterns, {"command": "safe", "file_path": "/project/.env"})
    assert result is not None


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


@given(value=st.text(max_size=200))
@settings(max_examples=300)
def test_contains_empty_always_matches(value: str) -> None:
    spec = {"contains": ""}
    assert Matcher.match_spec(spec, "f", value) is not None


@given(needle=st.text(min_size=1, max_size=20), haystack=st.text(max_size=200))
@settings(max_examples=300)
def test_contains_iff_substring(needle: str, haystack: str) -> None:
    spec = {"contains": needle}
    result = Matcher.match_spec(spec, "f", haystack)
    if needle in haystack:
        assert result is not None
    else:
        assert result is None


@given(name=st.text(min_size=1, max_size=30))
@settings(max_examples=200)
def test_exact_tool_name_match_iff_equal(name: str) -> None:
    assert Matcher.match_tool_name(name, name) is True


@given(
    pattern=st.text(min_size=1, max_size=10).filter(lambda s: "*" not in s and "?" not in s),
    name=st.text(min_size=1, max_size=10).filter(lambda s: "*" not in s and "?" not in s),
)
@settings(max_examples=200)
def test_exact_tool_name_no_wildcard(pattern: str, name: str) -> None:
    result = Matcher.match_tool_name(pattern, name)
    assert result == (pattern == name)
