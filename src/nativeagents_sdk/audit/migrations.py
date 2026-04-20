"""Schema migration framework for the audit SQLite database.

Migration functions transform schema version N to N+1. The current schema
is v1 — there are no pending migrations, but the framework is in place for
future use.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

CURRENT_SCHEMA_VERSION = 1

# Path to the DDL file
_DDL_PATH = Path(__file__).parent / "ddl.sql"


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Apply the DDL if the database is fresh, then migrate to CURRENT_SCHEMA_VERSION.

    This is idempotent: calling it on an already-initialised database is safe.
    """
    # Check if we have a meta table yet
    has_meta = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()

    if has_meta is None:
        # Fresh database: apply full DDL
        ddl = _DDL_PATH.read_text(encoding="utf-8")
        conn.executescript(ddl)
        conn.commit()
        return

    # Get current schema version
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if row is None:
        current_version = 0
    else:
        try:
            current_version = int(row[0])
        except (ValueError, TypeError):
            current_version = 0

    migrate(conn, target_version=CURRENT_SCHEMA_VERSION, from_version=current_version)


def migrate(
    conn: sqlite3.Connection,
    target_version: int = CURRENT_SCHEMA_VERSION,
    from_version: int | None = None,
) -> None:
    """Migrate the database from from_version to target_version.

    Args:
        conn: Open database connection.
        target_version: Version to migrate to. Defaults to CURRENT_SCHEMA_VERSION.
        from_version: Starting version. If None, reads from meta table.

    The migration list is empty for v1 — no structural changes yet.
    Future migrations are added as functions in the _MIGRATIONS list.
    """
    if from_version is None:
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        from_version = int(row[0]) if row else 0

    if from_version >= target_version:
        return  # Already at or beyond target

    # Walk migration steps: from_version → from_version+1 → ... → target_version
    for version in range(from_version, target_version):
        migration_fn = _MIGRATIONS.get(version)
        if migration_fn is not None:
            migration_fn(conn)
        # Update schema_version after each step
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(version + 1),),
        )
        conn.commit()


def _migrate_0_to_1(conn: sqlite3.Connection) -> None:
    """Migration from schema version 0 to 1.

    This applies the full v1 DDL to a database that was created before
    we tracked schema_version.
    """
    ddl = _DDL_PATH.read_text(encoding="utf-8")
    conn.executescript(ddl)
    conn.commit()


# Registry of migration functions: {from_version: migration_fn}
# Each function transforms the DB from `from_version` to `from_version + 1`.
_MigrationFn = Callable[[sqlite3.Connection], None]
_MIGRATIONS: dict[int, _MigrationFn] = {
    0: _migrate_0_to_1,
}
