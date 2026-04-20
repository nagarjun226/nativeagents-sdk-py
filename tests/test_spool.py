"""Tests for the Spool class."""

from __future__ import annotations

import threading

from nativeagents_sdk.spool.spool import Spool


def test_spool_write_creates_file(isolated_home):
    """Spool.write() creates a file in the spool directory."""
    spool = Spool("test-plugin", "audit")
    path = spool.write(b"hello world")
    assert path.exists()
    assert path.read_bytes() == b"hello world"


def test_spool_write_no_tmp_left(isolated_home):
    """Spool.write() leaves no temp files after successful write."""
    spool = Spool("test-plugin", "audit")
    spool.write(b"data")
    tmp_dir = spool._tmp_dir
    if tmp_dir.exists():
        tmp_files = list(tmp_dir.iterdir())
        assert tmp_files == []


def test_spool_iter_empty(isolated_home):
    """Spool.iter() on empty spool yields nothing."""
    spool = Spool("test-plugin", "audit")
    assert list(spool.iter()) == []


def test_spool_iter_returns_files(isolated_home):
    """Spool.iter() yields files in sorted (chronological) order."""
    spool = Spool("test-plugin", "audit")
    paths = [spool.write(f"item {i}".encode()) for i in range(3)]
    iterated = list(spool.iter())
    assert len(iterated) == 3
    # All written files should be returned
    assert set(iterated) == set(paths)


def test_spool_iter_skips_dotfiles(isolated_home):
    """Spool.iter() skips dotfiles (including .tmp dir)."""
    spool = Spool("test-plugin", "audit")
    spool.write(b"real data")
    # Create a dotfile manually
    spool.spool_path.mkdir(parents=True, exist_ok=True)
    dotfile = spool.spool_path / ".hidden"
    dotfile.write_bytes(b"hidden")

    iterated = list(spool.iter())
    assert all(not p.name.startswith(".") for p in iterated)


def test_spool_consume_deletes_file(isolated_home):
    """Spool.consume() deletes the file."""
    spool = Spool("test-plugin", "audit")
    path = spool.write(b"data")
    assert path.exists()
    spool.consume(path)
    assert not path.exists()


def test_spool_consume_idempotent(isolated_home):
    """Spool.consume() on already-deleted file is a no-op."""
    spool = Spool("test-plugin", "audit")
    path = spool.write(b"data")
    spool.consume(path)
    spool.consume(path)  # Should not raise


def test_spool_concurrent_writes(isolated_home):
    """Concurrent writes don't clobber each other."""
    spool = Spool("test-plugin", "audit")
    results = []
    errors = []

    def write_items() -> None:
        try:
            for i in range(20):
                p = spool.write(f"thread data {i}".encode())
                results.append(p)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))

    threads = [threading.Thread(target=write_items) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # All files should exist and have unique paths
    assert len(results) == len(set(results))
    for p in results:
        assert p.exists()


def test_spool_different_plugins_isolated(isolated_home):
    """Spools for different plugins are in different directories."""
    spool_a = Spool("plugin-a", "audit")
    spool_b = Spool("plugin-b", "audit")
    assert spool_a.spool_path != spool_b.spool_path


def test_spool_different_kinds_isolated(isolated_home):
    """Spools for different kinds (same plugin) are in different directories."""
    spool_audit = Spool("my-plugin", "audit")
    spool_inbox = Spool("my-plugin", "inbox")
    assert spool_audit.spool_path != spool_inbox.spool_path


def test_spool_write_returns_path_in_spool_dir(isolated_home):
    """Spool.write() returns a path in the spool directory (not .tmp/)."""
    spool = Spool("test-plugin", "audit")
    path = spool.write(b"data")
    assert path.parent == spool.spool_path
