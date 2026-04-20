"""Optional managed venv helpers for plugin installation."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def ensure_bin_dir() -> Path:
    """Create ~/.nativeagents/bin/ if it doesn't exist and return its path."""
    from nativeagents_sdk.paths import bin_dir, ensure_dir

    d = bin_dir()
    ensure_dir(d)
    return d


def create_venv(target: Path, python: str = "python3") -> Path:
    """Create a Python venv at target, returning the path to its Python executable.

    Args:
        target: Path where the venv should be created.
        python: Python executable to use (default: "python3").

    Returns:
        Path to the venv's Python executable.

    Raises:
        RuntimeError: If venv creation fails.
    """
    import venv as _venv

    if not target.exists():
        _venv.create(str(target), with_pip=True, clear=False)

    # Find the Python executable in the new venv
    candidates = [
        target / "bin" / "python3",
        target / "bin" / "python",
        target / "Scripts" / "python.exe",  # Windows
    ]
    for c in candidates:
        if c.exists():
            return c

    raise RuntimeError(f"Could not find Python executable in venv at {target}")


def install_package(venv_python: Path, package: str) -> None:
    """Install a package into a venv.

    Args:
        venv_python: Path to the venv's Python executable.
        package: Package spec (e.g., "nativeagents-sdk>=0.1").

    Raises:
        RuntimeError: If pip install fails.
    """
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", package],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pip install {package!r} failed:\n{result.stderr}")
