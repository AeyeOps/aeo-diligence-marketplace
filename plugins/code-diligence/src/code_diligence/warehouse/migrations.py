"""Versioned schema migrations for the warehouse.

For v1 there is only one migration: init the schema. Future schema
changes register a callable per target version. `migrate()` walks
from current_version up to SCHEMA_VERSION applying each.
"""
from collections.abc import Callable

import duckdb

from .schema import init_schema

MIGRATIONS: dict[int, Callable[[duckdb.DuckDBPyConnection], None]] = {
    1: init_schema,
    # v2: adds commit_file_authors (idempotent — init_schema's CREATE IF NOT EXISTS picks it up)
    2: init_schema,
}


def current_version(conn: duckdb.DuckDBPyConnection) -> int:
    """Return the highest applied schema version, or 0 if schema_version table missing."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    except duckdb.CatalogException:
        return 0
    return int(row[0]) if row and row[0] is not None else 0


def migrate(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply all pending migrations to bring warehouse to SCHEMA_VERSION."""
    cur = current_version(conn)
    for v in sorted(MIGRATIONS):
        if v > cur:
            MIGRATIONS[v](conn)
