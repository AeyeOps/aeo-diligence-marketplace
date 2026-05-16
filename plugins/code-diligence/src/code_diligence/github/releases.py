"""Fetch GitHub releases; populate release_metrics."""
from datetime import datetime

import duckdb

from .client import GitHubClient, paginate


def fetch_and_persist_releases(
    conn: duckdb.DuckDBPyConnection,
    *, repo_id: str, repo_full_name: str, token: str,
) -> None:
    client = GitHubClient(token=token)
    conn.execute("DELETE FROM release_metrics WHERE repo_id = ?", [repo_id])

    releases = list(paginate(client, f"/repos/{repo_full_name}/releases"))
    # Sort ascending by published_at so we can compute days_since_prev
    releases.sort(key=lambda r: r.get("published_at") or "")

    prev_at: datetime | None = None
    for rel in releases:
        published_at = _parse_iso(rel.get("published_at"))
        days_since_prev: float | None = None
        if published_at and prev_at:
            days_since_prev = (published_at - prev_at).total_seconds() / 86400.0
        conn.execute(
            "INSERT INTO release_metrics (repo_id, tag, released_at, days_since_prev) VALUES (?, ?, ?, ?)",
            [repo_id, rel.get("tag_name", ""), published_at, days_since_prev],
        )
        if published_at:
            prev_at = published_at


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
