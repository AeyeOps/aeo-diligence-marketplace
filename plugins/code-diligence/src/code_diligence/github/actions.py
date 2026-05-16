"""Fetch GitHub Actions workflow runs; populate actions_metrics."""
from datetime import datetime

import duckdb

from .client import GitHubClient, paginate


def fetch_and_persist_actions(
    conn: duckdb.DuckDBPyConnection,
    *, repo_id: str, repo_full_name: str, token: str,
) -> None:
    client = GitHubClient(token=token)
    conn.execute("DELETE FROM actions_metrics WHERE repo_id = ?", [repo_id])
    for run in paginate(client, f"/repos/{repo_full_name}/actions/runs"):
        ran_at = _parse_iso(run.get("created_at"))
        updated_at = _parse_iso(run.get("updated_at"))
        duration = (
            (updated_at - ran_at).total_seconds()
            if (ran_at and updated_at) else None
        )
        conn.execute(
            "INSERT INTO actions_metrics (repo_id, workflow_name, run_id, ran_at, conclusion, duration_seconds) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [repo_id, run.get("name", ""), run["id"], ran_at, run.get("conclusion"), duration],
        )


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
