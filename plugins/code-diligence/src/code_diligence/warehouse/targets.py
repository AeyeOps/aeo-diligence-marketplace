"""Target registration and lookup helpers."""
import json
from typing import Any

import duckdb


def register_target(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    name: str,
    description: str | None = None,
) -> None:
    """Insert or update a target row. Sets ingested_at on insert; refreshes last_refreshed_at on update."""
    existing = conn.execute(
        "SELECT target_id FROM targets WHERE target_id = ?", [target_id]
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE targets SET name = ?, description = ?, last_refreshed_at = CURRENT_TIMESTAMP WHERE target_id = ?",
            [name, description, target_id],
        )
    else:
        conn.execute(
            "INSERT INTO targets (target_id, name, description, ingested_at) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            [target_id, name, description],
        )


def update_tooling_versions(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    versions: dict[str, str],
) -> None:
    """Persist a {tool_name: version} mapping into targets.tooling_versions as JSON."""
    conn.execute(
        "UPDATE targets SET tooling_versions = ? WHERE target_id = ?",
        [json.dumps(versions), target_id],
    )


def get_target(conn: duckdb.DuckDBPyConnection, target_id: str) -> dict[str, Any] | None:
    """Fetch a target as a dict, or None if not found."""
    row = conn.execute(
        "SELECT target_id, name, description, ingested_at, last_refreshed_at, tooling_versions "
        "FROM targets WHERE target_id = ?",
        [target_id],
    ).fetchone()
    if row is None:
        return None
    return {
        "target_id": row[0],
        "name": row[1],
        "description": row[2],
        "ingested_at": row[3],
        "last_refreshed_at": row[4],
        "tooling_versions": row[5],
    }
