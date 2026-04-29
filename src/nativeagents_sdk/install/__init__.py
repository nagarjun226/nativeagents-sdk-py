"""Plugin installation and registration utilities."""

from nativeagents_sdk.install.doctor import DoctorReport, doctor
from nativeagents_sdk.install.register import (
    is_registered,
    read_claude_settings,
    register_plugin,
    unregister_plugin,
    write_claude_settings,
)
from nativeagents_sdk.install.shims import (
    shim_is_executable,
    write_capture_shim,
    write_decision_shim,
)

__all__ = [
    "register_plugin",
    "unregister_plugin",
    "is_registered",
    "read_claude_settings",
    "write_claude_settings",
    "doctor",
    "DoctorReport",
    # shim generation (v0.2)
    "write_decision_shim",
    "write_capture_shim",
    "shim_is_executable",
]
