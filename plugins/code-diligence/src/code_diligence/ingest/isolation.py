"""Keep a failed tool's writes out of the warehouse and record its failure."""
import json
import subprocess
from collections.abc import Callable
from typing import TypeVar

import duckdb
import httpx

from code_diligence.warehouse.failures import FailureClass, log_failure

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
    """Commit a tool's complete result, or roll back and report its boundary error."""
    conn.execute("BEGIN TRANSACTION")
    try:
        result = fn()
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError, httpx.HTTPError, duckdb.Error) as exc:
        conn.execute("ROLLBACK")
        failure_class: FailureClass = "crash"
        if isinstance(exc, FileNotFoundError):
            failure_class = "prereq_missing"
        elif isinstance(exc, (TimeoutError, subprocess.TimeoutExpired, httpx.TimeoutException)):
            failure_class = "timeout"
        elif isinstance(exc, json.JSONDecodeError):
            failure_class = "parse_error"
        log_failure(
            conn, target_id=target_id, repo_id=repo_id,
            tool=tool, tool_version=tool_version,
            failure_class=failure_class, message=f"{type(exc).__name__}: {exc}",
        )
        return None
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute(
            "DELETE FROM tool_failures WHERE target_id = ? AND repo_id IS NOT DISTINCT FROM ? AND tool = ?",
            [target_id, repo_id, tool],
        )
        conn.execute("COMMIT")
        return result
