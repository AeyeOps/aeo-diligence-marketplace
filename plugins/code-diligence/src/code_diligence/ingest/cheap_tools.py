"""Run the three cheap CLI tools per repo; persist to warehouse.

NOTE: per-tool parallelism within a single repo is deferred because DuckDB is
not threadsafe for concurrent writes from the same process. The higher-level
ingest loop runs repos in parallel; per-repo serial cost is acceptable and
side-steps DuckDB threading concerns.
"""
from collections.abc import Callable
from pathlib import Path

import duckdb

from code_diligence.ingest.isolation import isolated
from code_diligence.tools.git_fame import persist_git_fame, run_git_fame
from code_diligence.tools.git_of_theseus import persist_git_of_theseus, run_git_of_theseus
from code_diligence.tools.git_truck import persist_git_truck, run_git_truck


def run_cheap_tools_for_repo(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    repo_id: str,
    repo_path: Path,
    max_workers: int = 3,
) -> None:
    """Run git-fame, git-of-theseus, git-truck against repo_path; each isolated.

    The `max_workers` parameter is reserved for future per-tool parallelism;
    currently the function runs sequentially to avoid DuckDB concurrent-write
    issues.
    """
    def _gf() -> None:
        records = run_git_fame(repo_path)
        persist_git_fame(conn, repo_id=repo_id, records=records)

    def _got() -> None:
        buckets = run_git_of_theseus(repo_path)
        persist_git_of_theseus(conn, repo_id=repo_id, buckets=buckets)

    def _gt() -> None:
        records = run_git_truck(repo_path)
        persist_git_truck(conn, repo_id=repo_id, records=records)

    tasks: list[tuple[str, Callable[[], None]]] = [
        ("git-fame", _gf),
        ("git-of-theseus", _got),
        ("git-truck", _gt),
    ]
    for tool_name, fn in tasks:
        isolated(
            conn, target_id=target_id, repo_id=repo_id,
            tool=tool_name, tool_version=None,
            fn=fn,
        )
