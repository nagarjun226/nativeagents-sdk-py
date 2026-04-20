"""pytest configuration and shared fixtures.

The isolated_home fixture is autouse=True, so ALL tests run with
NATIVEAGENTS_HOME and CLAUDE_HOME redirected to tmp_path.
No test should ever touch the real ~/.nativeagents or ~/.claude.

Network access is disabled globally via pytest-socket; tests that genuinely
need a socket (e.g. subprocess-based SQLite multi-process) use a Unix-domain
socket on tmp_path and are not affected by this restriction.
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Redirect NATIVEAGENTS_HOME and CLAUDE_HOME to tmp_path for each test."""
    na_home = tmp_path / ".nativeagents"
    claude_home = tmp_path / ".claude"
    na_home.mkdir()
    claude_home.mkdir()
    monkeypatch.setenv("NATIVEAGENTS_HOME", str(na_home))
    monkeypatch.setenv("CLAUDE_HOME", str(claude_home))
    return na_home, claude_home
