"""Collect git-fame ownership by email, merging author-name aliases upstream."""
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class GitFameRecord:
    author_email: str
    owned_loc: int
    owned_commits: int
    owned_files: int


class GitFameError(RuntimeError):
    """Raised when git-fame subprocess fails."""


def run_git_fame(repo: Path) -> list[GitFameRecord]:
    """Spawn git-fame against repo and return parsed records."""
    proc = subprocess.run(
        ["git-fame", "--format=json", "--show=email", "--silent-progress", str(repo)],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise GitFameError(f"git-fame failed (exit {proc.returncode}): {proc.stderr.strip()}")
    return parse_git_fame_json(json.loads(proc.stdout))


def parse_git_fame_json(payload: dict[str, Any]) -> list[GitFameRecord]:
    """Parse git-fame --format=json --show=email ownership rows."""
    columns = payload["columns"]
    out = []
    for values in payload["data"]:
        row = dict(zip(columns, values, strict=True))
        out.append(GitFameRecord(
            author_email=row["Author"].strip().lower(),
            owned_loc=int(row["loc"]), owned_commits=int(row["coms"]), owned_files=int(row["fils"]),
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
