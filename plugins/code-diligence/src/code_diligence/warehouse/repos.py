"""Repo registration and lookup helpers."""
import json
from typing import Any

import duckdb


def upsert_repo(
    conn: duckdb.DuckDBPyConnection,
    *,
    repo_id: str,
    target_id: str,
    name: str,
    source_url: str,
    default_branch: str | None = None,
    language_primary: str | None = None,
    languages: dict[str, Any] | None = None,
    is_archived: bool = False,
    source_capability_flags: dict[str, Any] | None = None,
) -> None:
    """Insert or update a repo row. repo_id is the canonical key (typically '<org>/<repo>')."""
    languages_json = json.dumps(languages) if languages is not None else None
    flags_json = json.dumps(source_capability_flags) if source_capability_flags is not None else None
    existing = conn.execute("SELECT repo_id FROM repos WHERE repo_id = ?", [repo_id]).fetchone()
    if existing:
        conn.execute(
            "UPDATE repos SET target_id=?, name=?, source_url=?, default_branch=?, "
            "language_primary=?, languages=?, is_archived=?, source_capability_flags=? "
            "WHERE repo_id=?",
            [target_id, name, source_url, default_branch, language_primary,
             languages_json, is_archived, flags_json, repo_id],
        )
    else:
        conn.execute(
            "INSERT INTO repos (repo_id, target_id, name, source_url, default_branch, "
            "language_primary, languages, is_archived, source_capability_flags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [repo_id, target_id, name, source_url, default_branch, language_primary,
             languages_json, is_archived, flags_json],
        )


def get_repo(conn: duckdb.DuckDBPyConnection, repo_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT repo_id, target_id, name, source_url, default_branch, language_primary, "
        "languages, first_commit_at, last_commit_at, is_archived, source_capability_flags "
        "FROM repos WHERE repo_id = ?",
        [repo_id],
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_repos(conn: duckdb.DuckDBPyConnection, target_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT repo_id, target_id, name, source_url, default_branch, language_primary, "
        "languages, first_commit_at, last_commit_at, is_archived, source_capability_flags "
        "FROM repos WHERE target_id = ? ORDER BY repo_id",
        [target_id],
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "repo_id": row[0], "target_id": row[1], "name": row[2], "source_url": row[3],
        "default_branch": row[4], "language_primary": row[5], "languages": row[6],
        "first_commit_at": row[7], "last_commit_at": row[8], "is_archived": row[9],
        "source_capability_flags": row[10],
    }
