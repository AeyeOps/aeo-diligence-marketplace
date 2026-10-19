"""Fetch PRs; populate pr_metrics."""
from datetime import datetime

import duckdb

from .client import GitHubClient, paginate


def fetch_and_persist_prs(
    conn: duckdb.DuckDBPyConnection,
    *, repo_id: str, repo_full_name: str, token: str,
) -> None:
    with GitHubClient(token=token) as client:
        conn.execute("DELETE FROM pr_metrics WHERE repo_id = ?", [repo_id])
        for pr in paginate(client, f"/repos/{repo_full_name}/pulls", state="all"):
            conn.execute(
                "INSERT INTO pr_metrics (repo_id, pr_number, opened_at, merged_at, closed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                [repo_id, pr["number"], _parse_iso(pr.get("created_at")),
                 _parse_iso(pr.get("merged_at")), _parse_iso(pr.get("closed_at"))],
            )

def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
