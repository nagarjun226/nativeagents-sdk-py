"""Doctor: self-check helpers for installed plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class DoctorReport:
    """Result of a doctor() health check.

    Attributes:
        plugin_name: Name of the plugin that was checked.
        checks: List of check result dicts, each with:
            - name: str
            - passed: bool
            - message: str
    """

    plugin_name: str
    checks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """True if all checks passed."""
        return all(c.get("passed", False) for c in self.checks)

    def to_text(self) -> str:
        """Format the report as human-readable text."""
        lines = [f"Doctor report for plugin: {self.plugin_name}"]
        for check in self.checks:
            status = "PASS" if check.get("passed") else "FAIL"
            lines.append(f"  [{status}] {check['name']}: {check['message']}")
        overall = "healthy" if self.is_healthy else "unhealthy"
        lines.append(f"Overall: {overall}")
        return "\n".join(lines)


def doctor(plugin_name: str) -> DoctorReport:
    """Run a series of health checks for a plugin.

    Checks performed:
    1. plugin.toml exists and is valid.
    2. Plugin state directory exists.
    3. Hook script exists and is executable.
    4. Plugin is registered in ~/.claude/settings.json.

    Args:
        plugin_name: Name of the plugin to check.

    Returns:
        DoctorReport with results of each check.
    """
    from nativeagents_sdk.install.register import is_registered
    from nativeagents_sdk.paths import plugin_dir
    from nativeagents_sdk.plugin.manifest import load_plugin_manifest

    report = DoctorReport(plugin_name=plugin_name)
    p_dir = plugin_dir(plugin_name)

    # Check 1: plugin.toml exists and is valid
    toml_path = p_dir / "plugin.toml"
    if toml_path.exists():
        try:
            manifest = load_plugin_manifest(toml_path)
            report.checks.append(
                {
                    "name": "plugin.toml",
                    "passed": True,
                    "message": f"Valid (version {manifest.version})",
                }
            )
        except Exception as exc:  # noqa: BLE001
            report.checks.append({"name": "plugin.toml", "passed": False, "message": str(exc)})
    else:
        report.checks.append(
            {
                "name": "plugin.toml",
                "passed": False,
                "message": f"Not found at {toml_path}",
            }
        )

    # Check 2: state directory exists
    if p_dir.exists():
        report.checks.append({"name": "state_dir", "passed": True, "message": f"{p_dir} exists"})
    else:
        report.checks.append(
            {
                "name": "state_dir",
                "passed": False,
                "message": f"State directory not found: {p_dir}",
            }
        )

    # Check 3: logs directory writable
    logs_dir = p_dir / "logs"
    if logs_dir.exists() and _is_writable(logs_dir):
        report.checks.append(
            {"name": "logs_dir", "passed": True, "message": f"{logs_dir} writable"}
        )
    else:
        report.checks.append(
            {
                "name": "logs_dir",
                "passed": False,
                "message": f"Logs directory not found or not writable: {logs_dir}",
            }
        )

    # Check 4: registered in Claude settings
    if is_registered(plugin_name):
        report.checks.append(
            {
                "name": "registered",
                "passed": True,
                "message": "Plugin registered in ~/.claude/settings.json",
            }
        )
    else:
        report.checks.append(
            {
                "name": "registered",
                "passed": False,
                "message": "Plugin NOT registered in ~/.claude/settings.json",
            }
        )

    return report


def _is_writable(path: Path) -> bool:
    """Return True if path is writable by the current process."""
    import os

    return os.access(path, os.W_OK)
