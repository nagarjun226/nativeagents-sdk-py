"""Conformance harness: verify a plugin directory meets the SDK contract."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ConformanceReport:
    """Result of run_conformance().

    Attributes:
        plugin_dir: The directory that was checked.
        checks: List of check result dicts (name, passed, message).
    """

    plugin_dir: Path
    checks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all checks passed."""
        return all(c.get("passed", False) for c in self.checks)


def _ok(name: str, message: str) -> dict[str, Any]:
    """Return a passing check result dict."""
    return {"name": name, "passed": True, "message": message}


def _fail(name: str, message: str) -> dict[str, Any]:
    """Return a failing check result dict."""
    return {"name": name, "passed": False, "message": message}


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a PEP-440-ish version string into a comparable tuple."""
    try:
        return tuple(int(p) for p in v.split(".")[:3])
    except (ValueError, AttributeError):
        return (0,)


def run_conformance(plugin_dir: Path) -> ConformanceReport:
    """Run all conformance checks against a plugin directory.

    Checks (in order):
    1. plugin_toml_exists    — plugin.toml is present and readable.
    2. manifest_valid        — plugin.toml is valid TOML containing a [plugin] table.
    3. name_not_reserved     — plugin name is not in the SDK reserved set.
    4. sdk_version_satisfied — min_sdk_version <= installed nativeagents_sdk version.
    5. hooks_known           — every declared hook is a recognised Claude Code event.
    6. hook_script_exists    — hooks/hook.sh (or any .sh) is present when hooks declared.

    Args:
        plugin_dir: Root directory of the plugin (containing plugin.toml).

    Returns:
        ConformanceReport with a check dict for each check run.
    """
    report = ConformanceReport(plugin_dir=plugin_dir)

    # ------------------------------------------------------------------
    # Check 1: plugin.toml exists
    # ------------------------------------------------------------------
    toml_path = plugin_dir / "plugin.toml"
    if not toml_path.exists():
        report.checks.append(_fail("plugin_toml_exists", f"plugin.toml not found at {toml_path}"))
        return report

    report.checks.append(_ok("plugin_toml_exists", "plugin.toml found and readable"))

    # ------------------------------------------------------------------
    # Check 2: manifest_valid — TOML parses and has required structure
    # ------------------------------------------------------------------
    try:
        raw_text = toml_path.read_bytes().decode("utf-8")
        raw: Any = tomllib.loads(raw_text)
    except Exception as exc:  # noqa: BLE001
        report.checks.append(_fail("manifest_valid", f"plugin.toml parse error: {exc}"))
        return report

    if not isinstance(raw, dict) or "plugin" not in raw:
        report.checks.append(
            _fail("manifest_valid", "plugin.toml must be a TOML table with a [plugin] section")
        )
        return report

    plugin_section: dict[str, Any] = raw.get("plugin", {})
    name = plugin_section.get("name", "")
    ver = plugin_section.get("version", "?")
    report.checks.append(_ok("manifest_valid", f"manifest parsed OK (name={name!r} v{ver})"))

    # ------------------------------------------------------------------
    # Check 3: name_not_reserved
    # ------------------------------------------------------------------
    from nativeagents_sdk.paths import validate_plugin_name

    try:
        validate_plugin_name(name)
        report.checks.append(_ok("name_not_reserved", f"name {name!r} is not reserved"))
    except ValueError as exc:
        report.checks.append(_fail("name_not_reserved", str(exc)))

    # ------------------------------------------------------------------
    # Check 4: sdk_version_satisfied
    # ------------------------------------------------------------------
    from nativeagents_sdk.version import __version__ as installed_version

    min_ver: str | None = plugin_section.get("min_sdk_version")
    if min_ver is None:
        report.checks.append(
            _ok("sdk_version_satisfied", "min_sdk_version not declared (no constraint)")
        )
    elif _parse_version(min_ver) <= _parse_version(installed_version):
        report.checks.append(
            _ok("sdk_version_satisfied", f"min_sdk_version={min_ver!r} <= {installed_version!r}")
        )
    else:
        report.checks.append(
            _fail(
                "sdk_version_satisfied",
                f"Plugin requires SDK >= {min_ver!r}; installed {installed_version!r}",
            )
        )

    # ------------------------------------------------------------------
    # Check 5: hooks_known
    # ------------------------------------------------------------------
    from nativeagents_sdk.schema.plugin import VALID_HOOK_EVENTS

    declared_hooks: list[str] = plugin_section.get("hooks", [])
    unknown = [h for h in declared_hooks if h not in VALID_HOOK_EVENTS]
    if unknown:
        report.checks.append(
            _fail(
                "hooks_known",
                f"Unknown hook event(s): {unknown}. Expected one of: {sorted(VALID_HOOK_EVENTS)}",
            )
        )
    else:
        report.checks.append(
            _ok("hooks_known", f"All declared hooks are known: {declared_hooks or '(none)'}")
        )

    # ------------------------------------------------------------------
    # Check 6: hook_script_exists
    # ------------------------------------------------------------------
    if declared_hooks:
        hooks_dir = plugin_dir / "hooks"
        sh_files = list(hooks_dir.glob("*.sh")) if hooks_dir.exists() else []
        if sh_files:
            report.checks.append(
                _ok("hook_script_exists", f"Hook script found: {sh_files[0].name}")
            )
        else:
            report.checks.append(
                _fail("hook_script_exists", "Hooks declared but no .sh script found in hooks/")
            )

    return report
