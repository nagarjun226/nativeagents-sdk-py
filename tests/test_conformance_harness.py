"""Tests for the conformance harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from nativeagents_sdk.conformance.harness import ConformanceReport, run_conformance


def create_valid_plugin(tmp_path: Path, name: str = "test-plugin") -> Path:
    """Create a minimal valid plugin directory."""
    plugin_dir = tmp_path / name
    hooks_dir = plugin_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    (plugin_dir / "plugin.toml").write_text(
        f"""schema_version = 1

[plugin]
name = "{name}"
version = "0.1.0"
description = "A test plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = ["plugins/{name}/"]
hook_module = "{name.replace("-", "_")}.hook"
min_sdk_version = "0.1.0"
""",
        encoding="utf-8",
    )
    (hooks_dir / "hook.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    return plugin_dir


def test_run_conformance_valid_plugin(tmp_path, isolated_home):
    """run_conformance() passes for a valid plugin."""
    plugin_dir = create_valid_plugin(tmp_path)
    report = run_conformance(plugin_dir)
    failing = [c for c in report.checks if not c.get("passed")]
    assert report.passed, f"Expected pass, got breaks: {failing}"


def test_run_conformance_missing_toml(tmp_path, isolated_home):
    """run_conformance() fails when plugin.toml is missing."""
    empty = tmp_path / "empty"
    empty.mkdir()
    report = run_conformance(empty)
    assert not report.passed
    assert any(c["name"] == "plugin_toml_exists" and not c["passed"] for c in report.checks)


def test_run_conformance_report_structure(tmp_path, isolated_home):
    """ConformanceReport has expected structure."""
    plugin_dir = create_valid_plugin(tmp_path)
    report = run_conformance(plugin_dir)

    assert isinstance(report, ConformanceReport)
    assert report.plugin_dir == plugin_dir
    assert isinstance(report.checks, list)
    assert len(report.checks) > 0

    for check in report.checks:
        assert "name" in check
        assert "passed" in check
        assert "message" in check


def test_run_conformance_invalid_manifest(tmp_path, isolated_home):
    """run_conformance() fails for an invalid plugin.toml."""
    plugin_dir = tmp_path / "bad-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.toml").write_text("{invalid toml\n", encoding="utf-8")

    report = run_conformance(plugin_dir)
    assert not report.passed


def test_run_conformance_against_examples():
    """run_conformance() passes for the examples/minimal_plugin/ directory."""
    examples_dir = Path(__file__).parent.parent / "examples" / "minimal_plugin"
    if not examples_dir.exists():
        pytest.skip("examples/minimal_plugin/ not found")

    report = run_conformance(examples_dir)
    failed = [c for c in report.checks if not c.get("passed")]
    assert report.passed, f"Conformance failures: {failed}"
