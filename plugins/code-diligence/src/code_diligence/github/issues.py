"""Fetch GitHub issues; populate issue_metrics."""
from datetime import datetime
import json

import duckdb

from .client import GitHubClient, paginate


def fetch_and_persist_issues(
    conn: duckdb.DuckDBPyConnection,
    *, repo_id: str, repo_full_name: str, token: str,
) -> None:
    client = GitHubClient(token=token)
    conn.execute("DELETE FROM issue_metrics WHERE repo_id = ?", [repo_id])

    for issue in paginate(client, f"/repos/{repo_full_name}/issues", state="all", filter="all"):
        # GitHub issues endpoint returns PRs too; skip them
        if "pull_request" in issue:
            continue

        opened_at = _parse_iso(issue.get("created_at"))
        closed_at = _parse_iso(issue.get("closed_at"))
        labels = json.dumps([lb.get("name") for lb in issue.get("labels", [])])

        # Fetch first comment to compute days_to_first_response
        days_to_first_response: float | None = None
        comments_list = list(paginate(client, f"/repos/{repo_full_name}/issues/{issue['number']}/comments"))
        if comments_list and opened_at:
            first_comment_at = _parse_iso(comments_list[0].get("created_at"))
            if first_comment_at:
                days_to_first_response = (first_comment_at - opened_at).total_seconds() / 86400.0

        conn.execute(
            "INSERT INTO issue_metrics (repo_id, issue_number, opened_at, closed_at, state, labels, days_to_first_response) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [repo_id, issue["number"], opened_at, closed_at, issue.get("state"), labels, days_to_first_response],
        )


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
