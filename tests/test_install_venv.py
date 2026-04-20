"""Tests for install.venv module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_ensure_bin_dir_creates_directory(isolated_home: tuple[Path, Path]) -> None:
    """ensure_bin_dir() creates the bin directory and returns its path."""
    from nativeagents_sdk.install.venv import ensure_bin_dir
    from nativeagents_sdk.paths import bin_dir

    result = ensure_bin_dir()
    assert result.exists()
    assert result == bin_dir()


def test_ensure_bin_dir_idempotent(isolated_home: tuple[Path, Path]) -> None:
    """ensure_bin_dir() is safe to call multiple times."""
    from nativeagents_sdk.install.venv import ensure_bin_dir

    result1 = ensure_bin_dir()
    result2 = ensure_bin_dir()
    assert result1 == result2
    assert result2.exists()


def test_create_venv_returns_python_path(isolated_home: tuple[Path, Path], tmp_path: Path) -> None:
    """create_venv() returns the path to the venv's Python executable."""
    from nativeagents_sdk.install.venv import create_venv

    venv_dir = tmp_path / "test-venv"
    # This actually creates a real venv — mark as potentially slow
    python_path = create_venv(venv_dir)
    assert python_path.exists()
    assert "python" in python_path.name.lower()


def test_create_venv_skips_if_exists(isolated_home: tuple[Path, Path], tmp_path: Path) -> None:
    """create_venv() doesn't recreate if venv already exists."""
    from nativeagents_sdk.install.venv import create_venv

    venv_dir = tmp_path / "existing-venv"

    # Create first time
    python1 = create_venv(venv_dir)
    mtime1 = venv_dir.stat().st_mtime

    # Call again — should skip creation
    python2 = create_venv(venv_dir)
    mtime2 = venv_dir.stat().st_mtime

    assert python1 == python2
    assert mtime1 == mtime2  # directory unchanged


def test_install_package_success(isolated_home: tuple[Path, Path], tmp_path: Path) -> None:
    """install_package() calls pip install with correct args."""
    from nativeagents_sdk.install.venv import install_package

    venv_python = tmp_path / "python"

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        install_package(venv_python, "some-package>=1.0")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert str(venv_python) in args
        assert "some-package>=1.0" in args


def test_install_package_failure_raises(isolated_home: tuple[Path, Path], tmp_path: Path) -> None:
    """install_package() raises RuntimeError when pip fails."""
    from nativeagents_sdk.install.venv import install_package

    venv_python = tmp_path / "python"

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "ERROR: Package not found"

    with (
        patch("subprocess.run", return_value=mock_result),
        pytest.raises(RuntimeError, match="pip install"),
    ):
        install_package(venv_python, "nonexistent-package")
