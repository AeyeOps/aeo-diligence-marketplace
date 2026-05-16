"""Per-repo per-tool isolation: catch, log to tool_failures, return None."""
from collections.abc import Callable
from typing import TypeVar

import duckdb

from code_diligence.warehouse.failures import log_failure

T = TypeVar("T")


def isolated(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    repo_id: str | None,
    tool: str,
    tool_version: str | None,
    fn: Callable[[], T],
) -> T | None:
    """Run fn(); on exception, log to tool_failures and return None."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        log_failure(
            conn, target_id=target_id, repo_id=repo_id,
            tool=tool, tool_version=tool_version,
            failure_class="crash", message=f"{type(exc).__name__}: {exc}",
        )
        return None
