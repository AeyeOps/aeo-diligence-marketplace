"""Wrapper for casperdcl/git-fame (per-author LOC/commits/files attribution).

git-fame is a CLI: `git fame --json --silent-progress -e <repo>`.
We parse its JSON output into GitFameRecord and persist to ownership_share.
"""
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class GitFameRecord:
    author_name: str
    author_email: str
    owned_loc: int
    owned_commits: int
    owned_files: int


class GitFameError(RuntimeError):
    """Raised when git-fame subprocess fails."""


def run_git_fame(repo: Path) -> list[GitFameRecord]:
    """Spawn git-fame against repo and return parsed records."""
    proc = subprocess.run(
        ["git", "fame", "--json", "--silent-progress", "-e", "--bytype",
         "--git-dir", str(repo / ".git"), str(repo)],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise GitFameError(f"git-fame failed (exit {proc.returncode}): {proc.stderr.strip()}")
    return parse_git_fame_json(json.loads(proc.stdout))


def parse_git_fame_json(payload: dict[str, Any]) -> list[GitFameRecord]:
    """Parse git-fame --json output. Format: {columns: [...], data: [[...]]}."""
    cols = payload.get("columns", [])
    data = payload.get("data", [])
    # Find column indices defensively
    idx_name = cols.index("Author") if "Author" in cols else 0
    idx_email = cols.index("Email") if "Email" in cols else 1
    idx_loc = cols.index("loc") if "loc" in cols else 2
    idx_coms = cols.index("coms") if "coms" in cols else 3
    idx_fils = cols.index("fils") if "fils" in cols else 4
    out: list[GitFameRecord] = []
    for row in data:
        out.append(GitFameRecord(
            author_name=str(row[idx_name]).strip(),
            author_email=str(row[idx_email]).strip().lower(),
            owned_loc=int(row[idx_loc]),
            owned_commits=int(row[idx_coms]),
            owned_files=int(row[idx_fils]),
        ))
    return out


def persist_git_fame(
    conn: duckdb.DuckDBPyConnection,
    *,
    repo_id: str,
    records: list[GitFameRecord],
) -> None:
    conn.execute(
        "DELETE FROM ownership_share WHERE repo_id = ? AND source = 'git-fame'",
        [repo_id],
    )
    if not records:
        return
    rows = [
        (repo_id, r.author_email, r.owned_loc, r.owned_files, "git-fame")
        for r in records
    ]
    conn.executemany(
        "INSERT INTO ownership_share (repo_id, author_email, owned_loc, owned_files, source) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
