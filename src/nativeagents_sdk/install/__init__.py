"""Plugin installation and registration utilities."""

from nativeagents_sdk.install.doctor import DoctorReport, doctor
from nativeagents_sdk.install.register import (
    is_registered,
    read_claude_settings,
    register_plugin,
    unregister_plugin,
    write_claude_settings,
)

__all__ = [
    "register_plugin",
    "unregister_plugin",
    "is_registered",
    "read_claude_settings",
    "write_claude_settings",
    "doctor",
    "DoctorReport",
]
