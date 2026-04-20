"""Spool: atomic-rename file queue for plugin-to-plugin and plugin-to-sidecar messaging."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class Spool:
    """An atomic-rename spool directory for deferred plugin writes.

    Files are written atomically to a per-plugin, per-kind directory under
    ~/.nativeagents/spool/<plugin_name>/<kind>/

    The spool is content-agnostic (opaque bytes). Filenames are
    timestamp-prefixed for chronological iteration via sorted().

    Usage:
        spool = Spool("my-plugin", "audit")
        path = spool.write(b"my data")
        for p in spool.iter():
            data = p.read_bytes()
            process(data)
            spool.consume(p)
    """

    def __init__(self, plugin_name: str, kind: str) -> None:
        """Create a Spool instance.

        Args:
            plugin_name: Plugin name (used for directory namespacing).
            kind: Spool kind, e.g. "audit", "inbox", "outbound".
        """
        from nativeagents_sdk.paths import spool_dir

        self._spool_dir = spool_dir() / plugin_name / kind
        self._tmp_dir = self._spool_dir / ".tmp"

    @property
    def spool_path(self) -> Path:
        """The spool directory path."""
        return self._spool_dir

    def _ensure_dirs(self) -> None:
        """Create spool and tmp directories if they don't exist."""
        self._spool_dir.mkdir(parents=True, exist_ok=True)
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    def write(self, data: bytes) -> Path:
        """Write data to the spool atomically.

        Algorithm:
        1. Write to .tmp/<pid>-<random>.bin
        2. fsync
        3. os.replace() into spool dir with timestamp-prefixed name

        Args:
            data: Raw bytes to spool.

        Returns:
            Final path of the spooled file.
        """
        self._ensure_dirs()

        # Write to temp file
        tmp_name = f"{os.getpid()}-{secrets.token_hex(4)}.bin"
        tmp_path = self._tmp_dir / tmp_name

        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        # Final name: <iso-timestamp-colons-replaced>-<random>.bin
        ts = datetime.now(UTC).isoformat().replace(":", "-")
        final_name = f"{ts}-{secrets.token_hex(4)}.bin"
        final_path = self._spool_dir / final_name

        os.replace(tmp_path, final_path)
        return final_path

    def iter(self) -> Iterator[Path]:
        """Yield spool files in chronological (sorted filename) order.

        Skips .tmp/ directory and any dotfiles.

        Yields:
            Path to each spool file.
        """
        if not self._spool_dir.exists():
            return

        for name in sorted(p.name for p in self._spool_dir.iterdir()):
            if name.startswith("."):
                continue
            path = self._spool_dir / name
            if path.is_file():
                yield path

    def consume(self, path: Path) -> None:
        """Delete a spool file after successful processing.

        Idempotent: if the file no longer exists, this is a no-op.

        Args:
            path: Path returned by write() or iter().
        """
        path.unlink(missing_ok=True)
