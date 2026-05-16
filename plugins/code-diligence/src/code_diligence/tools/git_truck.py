"""Wrapper for git-truck v3 (per-file dominant-author analysis).

git-truck v3 is a long-running web app (Express + React Router v7), not a CLI
exporter — `--headless` only suppresses the browser auto-open; the server still
runs until SIGTERM. v3 uses DuckDB internally and writes its analysis to a
deterministic cache path. The wrapper drives it as follows:

  1. Spawn `npx -y git-truck@<pinned> --headless` with subprocess `cwd=<repo>`
     (positional repo argv is ignored by v3; the server defaults to `process.cwd()`).
  2. Drain stdout to extract the Express listening port.
  3. HTTP GET `/view` to kick the analysis loader (`viewMiddleware`). Fire-and-
     forget — the actual completion signal comes from metadata.json.
  4. Poll `$TMPDIR/git-truck-cache/metadata.json` until
     `completions["<absRepoPath>---<branch>"]` appears.
  5. SIGTERM the process group so DuckDB writes flush cleanly via the v3
     `stopHandler -> InstanceManager.closeAllDBConnections` path.
  6. Open the per-repo DuckDB cache read-only and run the same dominant-author
     SQL the v3 client uses (extracted verbatim from the bundled server).

Cache path layout (from v3 source):
  $TMPDIR/git-truck-cache/metadata.json
  $TMPDIR/git-truck-cache/<sanitized_repo_path>/<sanitized_branch>.db

where sanitize(s) = re.sub(r'\\W', '_', s) + '_'.

git-truck reports contributor names but not emails, so `persist_git_truck`
synthesizes a `name:<slug>` pseudo-email. The canonical ownership source remains
git-fame; git-truck rows exist for cross-check (source='git-truck').
"""
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import duckdb


GIT_TRUCK_VERSION = "3.3.0"

_PORT_RE = re.compile(r"http://localhost:(\d{4,5})")
_NONWORD_RE = re.compile(r"\W")
_PORT_WAIT_TIMEOUT_S = 120
_ANALYSIS_TIMEOUT_S = 180
_VIEW_KICK_TIMEOUT_S = 180
_SIGTERM_GRACE_S = 10
_POLL_INTERVAL_S = 0.4

# Adapted from git-truck v3's getDominantAuthorPerFile. The original query reads
# from filechanges_commits_renamed_cached, which is an in-memory materialized
# table created on the writer connection and not persisted. The base view
# filechanges_commits_renamed (same columns) IS persisted to disk by DuckDB,
# so a fresh read-only connection can query it directly.
_DOMINANT_AUTHOR_SQL = """
WITH RankedAuthors AS (
    SELECT filepath,
           author,
           SUM(insertions + deletions) AS contribcount,
           ROW_NUMBER() OVER (
               PARTITION BY filepath
               ORDER BY SUM(insertions + deletions) DESC, author ASC
           ) AS rank
    FROM filechanges_commits_renamed
    GROUP BY filepath, author
)
SELECT author,
       SUM(contribcount) AS owned_loc,
       COUNT(*) AS owned_files
FROM RankedAuthors
WHERE rank = 1
GROUP BY author
"""


@dataclass(frozen=True)
class GitTruckOwnership:
    author_name: str
    author_email: str | None
    owned_loc: int
    owned_files: int


class GitTruckError(RuntimeError):
    pass


def _sanitize(s: str) -> str:
    return _NONWORD_RE.sub("_", s) + "_"


def _abs_repo(repo: Path) -> str:
    """Match the cwd that git-truck sees: on macOS the kernel realpaths a
    subprocess's cwd, so /var/folders/... arrives as /private/var/folders/... .
    git-truck stores the completion key under that resolved form, so we follow
    symlinks here to keep the polling key in sync."""
    return os.path.realpath(str(repo))


def _detect_branch(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        raise GitTruckError(f"git rev-parse failed in {repo}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _cache_root() -> Path:
    return Path(tempfile.gettempdir()) / "git-truck-cache"


def _db_path(repo_abs: str, branch: str) -> Path:
    return _cache_root() / _sanitize(repo_abs) / f"{_sanitize(branch)}.db"


def _wait_for_port(proc: subprocess.Popen, deadline: float, log: list[str]) -> int:
    while time.time() < deadline:
        if proc.poll() is not None:
            tail = " | ".join(log[-6:])
            raise GitTruckError(
                f"git-truck exited before port appeared (rc={proc.returncode}); tail: {tail}"
            )
        assert proc.stdout is not None
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        log.append(line.rstrip())
        m = _PORT_RE.search(line)
        if m:
            return int(m.group(1))
    raise GitTruckError(f"git-truck never printed port within {_PORT_WAIT_TIMEOUT_S}s")


def _kick_view(port: int) -> threading.Thread:
    """Trigger the viewMiddleware analysis loader on a background thread.

    React Router v7 aborts the loader's async work when the client disconnects,
    so we cannot fire-and-forget with a short timeout — that interrupts the
    analysis we're trying to drive. Run the request on a daemon thread with a
    long timeout so the server completes its work uninterrupted while the main
    flow polls metadata.json for the completion signal."""
    url = f"http://127.0.0.1:{port}/view"

    def _hit() -> None:
        try:
            with urllib.request.urlopen(url, timeout=_VIEW_KICK_TIMEOUT_S):
                pass
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            pass

    t = threading.Thread(target=_hit, daemon=True)
    t.start()
    return t


def _wait_for_completion(repo_abs: str, branch: str, deadline: float) -> None:
    key = f"{repo_abs}---{branch}"
    metadata = _cache_root() / "metadata.json"
    while time.time() < deadline:
        try:
            data = json.loads(metadata.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            data = None
        if data and data.get("completions", {}).get(key):
            return
        time.sleep(_POLL_INTERVAL_S)
    raise GitTruckError(
        f"git-truck analysis did not complete within {_ANALYSIS_TIMEOUT_S}s for {repo_abs}"
    )


def _terminate(proc: subprocess.Popen) -> None:
    """SIGTERM the process group (npx spawns child processes); SIGKILL fallback."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=_SIGTERM_GRACE_S)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _query_ownership(db_path: Path) -> list[GitTruckOwnership]:
    if not db_path.exists():
        raise GitTruckError(f"git-truck cache DB not found at {db_path}")
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(_DOMINANT_AUTHOR_SQL).fetchall()
    finally:
        conn.close()
    return [
        GitTruckOwnership(
            author_name=author,
            author_email=None,
            owned_loc=int(loc),
            owned_files=int(files),
        )
        for author, loc, files in rows
    ]


def run_git_truck(repo: Path) -> list[GitTruckOwnership]:
    if not shutil.which("npx"):
        raise GitTruckError("npx not on PATH; install Node 20+")
    if not (repo / ".git").exists():
        raise GitTruckError(f"not a git repository: {repo}")

    branch = _detect_branch(repo)
    repo_abs = _abs_repo(repo)
    db_path = _db_path(repo_abs, branch)

    proc = subprocess.Popen(
        ["npx", "-y", f"git-truck@{GIT_TRUCK_VERSION}", "--headless"],
        cwd=repo_abs,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "HOST": "127.0.0.1"},
        start_new_session=True,
    )
    log: list[str] = []
    try:
        port = _wait_for_port(proc, time.time() + _PORT_WAIT_TIMEOUT_S, log)
        _kick_view(port)
        _wait_for_completion(repo_abs, branch, time.time() + _ANALYSIS_TIMEOUT_S)
    finally:
        _terminate(proc)
    return _query_ownership(db_path)


def persist_git_truck(
    conn: duckdb.DuckDBPyConnection,
    *,
    repo_id: str,
    records: list[GitTruckOwnership],
) -> None:
    conn.execute(
        "DELETE FROM ownership_share WHERE repo_id = ? AND source = 'git-truck'",
        [repo_id],
    )
    if not records:
        return
    rows = [
        (
            repo_id,
            f"name:{r.author_name.lower().replace(' ', '_')}",
            r.owned_loc,
            r.owned_files,
            "git-truck",
        )
        for r in records
    ]
    conn.executemany(
        "INSERT INTO ownership_share (repo_id, author_email, owned_loc, owned_files, source) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
