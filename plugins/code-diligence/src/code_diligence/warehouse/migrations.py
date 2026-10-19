"""Apply registered migrations in version order to existing warehouses."""
from collections.abc import Callable

import duckdb

from .schema import init_schema


def _preserve_repowise_hits(conn: duckdb.DuckDBPyConnection) -> None:
    """Retain every provider finding without assuming file/type uniqueness."""
    conn.execute("""
        BEGIN TRANSACTION;
        CREATE TABLE repowise_findings_v3 (
            repo_id VARCHAR NOT NULL,
            scope VARCHAR NOT NULL,
            finding_type VARCHAR NOT NULL,
            severity VARCHAR,
            evidence JSON
        );
        INSERT INTO repowise_findings_v3 SELECT * FROM repowise_findings;
        DROP TABLE repowise_findings;
        ALTER TABLE repowise_findings_v3 RENAME TO repowise_findings;
        INSERT INTO schema_version (version)
        SELECT 3 WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = 3);
        COMMIT;
    """)


def _drop_pr_review_fields(conn: duckdb.DuckDBPyConnection) -> None:
    """Remove PR review fields; GitHub review records do not show review done outside GitHub."""
    columns = ("review_latency_hours", "num_reviewers", "approvals", "lines_changed", "was_self_merged")
    conn.execute("BEGIN TRANSACTION")
    for column in columns:
        conn.execute(f"ALTER TABLE pr_metrics DROP COLUMN IF EXISTS {column}")
    conn.execute(
        "INSERT INTO schema_version (version) SELECT 4 WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = 4)"
    )
    conn.execute("COMMIT")


MIGRATIONS: dict[int, Callable[[duckdb.DuckDBPyConnection], None]] = {
    1: init_schema,
    2: init_schema,
    3: _preserve_repowise_hits,
    4: _drop_pr_review_fields,
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
