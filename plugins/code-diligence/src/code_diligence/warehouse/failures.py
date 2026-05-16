"""Tool failure logging."""
from typing import Any, Literal

import duckdb

FailureClass = Literal["crash", "timeout", "parse_error", "data_sanity"]


def log_failure(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    tool: str,
    failure_class: FailureClass,
    repo_id: str | None = None,
    tool_version: str | None = None,
    message: str | None = None,
) -> None:
    """Append a row to tool_failures."""
    conn.execute(
        "INSERT INTO tool_failures (target_id, repo_id, tool, tool_version, class, message) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [target_id, repo_id, tool, tool_version, failure_class, message],
    )


def list_failures(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    tool: str | None = None,
) -> list[dict[str, Any]]:
    """List failures for a target, optionally filtered by tool."""
    if tool is None:
        rows = conn.execute(
            "SELECT target_id, repo_id, tool, tool_version, class, message, occurred_at "
            "FROM tool_failures WHERE target_id = ? ORDER BY occurred_at DESC",
            [target_id],
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT target_id, repo_id, tool, tool_version, class, message, occurred_at "
            "FROM tool_failures WHERE target_id = ? AND tool = ? ORDER BY occurred_at DESC",
            [target_id, tool],
        ).fetchall()
    return [
        {
            "target_id": r[0], "repo_id": r[1], "tool": r[2], "tool_version": r[3],
            "class": r[4], "message": r[5], "occurred_at": r[6],
        }
        for r in rows
    ]
