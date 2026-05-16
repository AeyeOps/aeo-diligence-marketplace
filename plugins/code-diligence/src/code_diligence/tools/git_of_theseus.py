"""Wrapper for git-of-theseus (code-age cohort analysis).

CLI: `git-of-theseus-analyze <repo> --outdir <dir>` writes `cohorts.json`.
We parse the latest snapshot, bucket by vintage year, and persist to
`code_age_buckets`.
"""
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class CodeAgeBucket:
    bucket_start_year: int
    surviving_loc: int


class GitOfTheseusError(RuntimeError):
    """Raised when git-of-theseus subprocess fails."""


def run_git_of_theseus(repo: Path) -> list[CodeAgeBucket]:
    """Spawn git-of-theseus-analyze and parse the cohorts.json it writes."""
    with tempfile.TemporaryDirectory() as outdir:
        proc = subprocess.run(
            ["git-of-theseus-analyze", str(repo), "--outdir", outdir],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            raise GitOfTheseusError(
                f"git-of-theseus failed (exit {proc.returncode}): {proc.stderr.strip()}"
            )
        cohorts_path = Path(outdir) / "cohorts.json"
        return parse_cohorts_json(json.loads(cohorts_path.read_text()))


def parse_cohorts_json(payload: dict[str, Any]) -> list[CodeAgeBucket]:
    """Take the latest snapshot from a cohorts.json payload; bucket by year.

    cohorts.json shape: {"y": [[loc_per_cohort_at_t0], ...], "ts": [...], "labels": ["cohort1", ...]}
    """
    if not payload.get("y"):
        return []
    latest = payload["y"][-1]
    labels = payload.get("labels", [])
    out: list[CodeAgeBucket] = []
    for label, loc in zip(labels, latest, strict=False):
        # Labels are typically year-month or year strings; normalize to year
        try:
            year = int(str(label)[:4])
        except ValueError:
            continue
        out.append(CodeAgeBucket(bucket_start_year=year, surviving_loc=int(loc)))
    return out


def persist_git_of_theseus(
    conn: duckdb.DuckDBPyConnection,
    *,
    repo_id: str,
    buckets: list[CodeAgeBucket],
) -> None:
    """Replace code_age_buckets rows for repo_id with the given buckets."""
    conn.execute("DELETE FROM code_age_buckets WHERE repo_id = ?", [repo_id])
    if not buckets:
        return
    rows = [(repo_id, b.bucket_start_year, b.surviving_loc, 0) for b in buckets]
    conn.executemany(
        "INSERT INTO code_age_buckets (repo_id, bucket_start_year, surviving_loc, deleted_loc) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )
