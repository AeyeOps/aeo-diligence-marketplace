"""Fetch PRs + reviews; populate pr_metrics."""
from datetime import datetime
from typing import Any

import duckdb

from .client import GitHubClient, paginate


def fetch_and_persist_prs(
    conn: duckdb.DuckDBPyConnection,
    *, repo_id: str, repo_full_name: str, token: str,
) -> None:
    client = GitHubClient(token=token)
    conn.execute("DELETE FROM pr_metrics WHERE repo_id = ?", [repo_id])
    for pr in paginate(client, f"/repos/{repo_full_name}/pulls", state="all"):
        reviews = list(paginate(client, f"/repos/{repo_full_name}/pulls/{pr['number']}/reviews"))
        opened_at = _parse_iso(pr.get("created_at"))
        merged_at = _parse_iso(pr.get("merged_at"))
        closed_at = _parse_iso(pr.get("closed_at"))
        first_review_at = min(
            (_parse_iso(r["submitted_at"]) for r in reviews if r.get("submitted_at")),
            default=None,
        )
        review_latency = (
            (first_review_at - opened_at).total_seconds() / 3600.0
            if (first_review_at and opened_at) else None
        )
        approvals = sum(1 for r in reviews if r.get("state") == "APPROVED")
        author = (pr.get("user") or {}).get("login")
        merger = (pr.get("merged_by") or {}).get("login")
        was_self_merged = bool(merger and author and merger == author)
        conn.execute(
            "INSERT INTO pr_metrics (repo_id, pr_number, opened_at, merged_at, closed_at, "
            "review_latency_hours, num_reviewers, approvals, lines_changed, was_self_merged) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [repo_id, pr["number"], opened_at, merged_at, closed_at, review_latency,
             len({r.get("user", {}).get("login") for r in reviews if r.get("user")}),
             approvals, (pr.get("additions", 0) + pr.get("deletions", 0)), was_self_merged],
        )


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
