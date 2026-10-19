"""Persist walker output into git-only warehouse tables."""
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import duckdb

from .walker import CommitRecord


def persist_repo_git_facts(
    conn: duckdb.DuckDBPyConnection,
    *,
    repo_id: str,
    commits: Iterable[CommitRecord],
    head_paths: set[str],
) -> None:
    """Idempotent upsert: commits_fact, authors, file_metrics; updates repos.first/last_commit_at."""
    commits = list(commits)
    target_row = conn.execute(
        "SELECT target_id FROM repos WHERE repo_id = ?", [repo_id]
    ).fetchone()
    if target_row is None:
        raise ValueError(f"repo {repo_id} not registered")
    target_id = target_row[0]

    conn.execute("DELETE FROM commits_fact WHERE repo_id = ?", [repo_id])
    conn.execute("DELETE FROM commit_file_authors WHERE repo_id = ?", [repo_id])
    rows_commits = []
    rows_edges = []
    for c in commits:
        files_changed = len(c.file_changes)
        lines_added = sum(fc.lines_added for fc in c.file_changes)
        lines_removed = sum(fc.lines_removed for fc in c.file_changes)
        is_revert = c.message_first_line.lower().startswith(("revert ", "revert:"))
        rows_commits.append((
            repo_id, c.sha, c.author_email, c.author_date,
            files_changed, lines_added, lines_removed,
            c.is_merge, is_revert, c.message_first_line[:500],
        ))
        for fc in c.file_changes:
            rows_edges.append((
                repo_id, c.sha, c.author_email, c.author_date,
                fc.path, fc.lines_added, fc.lines_removed,
            ))
    if rows_commits:
        conn.executemany(
            "INSERT INTO commits_fact (repo_id, commit_sha, author_email, author_date, "
            "files_changed, lines_added, lines_removed, is_merge, is_revert, message_first_line) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows_commits,
        )
    if rows_edges:
        conn.executemany(
            "INSERT INTO commit_file_authors "
            "(repo_id, commit_sha, author_email, author_date, file_path, lines_added, lines_removed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows_edges,
        )

    by_email: dict[str, dict[str, Any]] = defaultdict(lambda: {"first": None, "last": None, "count": 0, "name": None})
    for c in commits:
        bucket = by_email[c.author_email]
        bucket["first"] = c.author_date if bucket["first"] is None or c.author_date < bucket["first"] else bucket["first"]
        bucket["last"]  = c.author_date if bucket["last"]  is None or c.author_date > bucket["last"]  else bucket["last"]
        bucket["count"] += 1
        bucket["name"] = c.author_name
    for email, b in by_email.items():
        existing = conn.execute(
            "SELECT author_email FROM authors WHERE author_email = ? AND target_id = ?",
            [email, target_id],
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE authors SET display_name = ?, "
                "first_seen = LEAST(COALESCE(first_seen, ?), ?), "
                "last_seen  = GREATEST(COALESCE(last_seen, ?), ?), "
                "total_commits = ? "
                "WHERE author_email = ? AND target_id = ?",
                [b["name"], b["first"], b["first"], b["last"], b["last"], b["count"], email, target_id],
            )
        else:
            conn.execute(
                "INSERT INTO authors (author_email, target_id, display_name, "
                "first_seen, last_seen, total_commits) VALUES (?, ?, ?, ?, ?, ?)",
                [email, target_id, b["name"], b["first"], b["last"], b["count"]],
            )

    conn.execute("""
        UPDATE authors AS a SET
          first_seen = stats.first_seen,
          last_seen = stats.last_seen,
          total_commits = stats.total_commits,
          is_active_l90 = stats.last_seen >= CURRENT_TIMESTAMP - INTERVAL '90 days'
        FROM (
          SELECT cf.author_email, MIN(cf.author_date) AS first_seen,
                 MAX(cf.author_date) AS last_seen, COUNT(*) AS total_commits
          FROM commits_fact cf JOIN repos r USING (repo_id)
          WHERE r.target_id = ? GROUP BY cf.author_email
        ) stats
        WHERE a.target_id = ? AND a.author_email = stats.author_email
    """, [target_id, target_id])
    conn.execute("""
        DELETE FROM authors AS a WHERE a.target_id = ? AND NOT EXISTS (
          SELECT 1 FROM commits_fact cf JOIN repos r USING (repo_id)
          WHERE r.target_id = a.target_id AND cf.author_email = a.author_email
        )
    """, [target_id])

    conn.execute("DELETE FROM file_metrics WHERE repo_id = ?", [repo_id])
    file_rev: dict[str, dict[str, Any]] = defaultdict(lambda: {"revisions": 0, "authors": set(), "last": None})
    for c in commits:
        for fc in c.file_changes:
            f = file_rev[fc.path]
            f["revisions"] += 1
            f["authors"].add(c.author_email)
            f["last"] = c.author_date if f["last"] is None or c.author_date > f["last"] else f["last"]
    rows_files = [
        (repo_id, path, m["revisions"], len(m["authors"]), m["last"], path in head_paths)
        for path, m in file_rev.items()
    ]
    rows_files += [(repo_id, path, 0, 0, None, True) for path in sorted(head_paths - file_rev.keys())]
    if rows_files:
        conn.executemany(
            "INSERT INTO file_metrics (repo_id, path, revisions, total_authors, last_modified_at, in_head) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows_files,
        )

    first = min((c.author_date for c in commits), default=None)
    last = max((c.author_date for c in commits), default=None)
    conn.execute(
        "UPDATE repos SET first_commit_at = ?, last_commit_at = ? WHERE repo_id = ?",
        [first, last, repo_id],
    )
