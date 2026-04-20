"""Tests for minimal-plugin."""

import minimal_plugin


def test_version() -> None:
    assert minimal_plugin.__version__ == "0.1.0"


def test_both_handlers_registered() -> None:
    from minimal_plugin.hook import dispatcher

    assert dispatcher is not None
    assert "PreToolUse" in dispatcher._handlers
    assert "PostToolUse" in dispatcher._handlers
