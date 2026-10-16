"""Drive git-truck in a fresh cache and read its completed ownership analysis."""
import json
import os
import queue
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


def _db_path(repo_abs: str, branch: str, cache_root: Path) -> Path:
    return cache_root / _sanitize(repo_abs) / f"{_sanitize(branch)}.db"


def _wait_for_port(proc: subprocess.Popen, deadline: float, log: list[str], output: queue.Queue) -> int:
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            line = output.get(timeout=max(0.01, remaining))
        except queue.Empty:
            break
        if line is None:
            raise GitTruckError(f"git-truck exited before announcing its port: {' | '.join(log[-6:])}")
        log.append(line.rstrip())
        match = _PORT_RE.search(line)
        if match:
            return int(match[1])
    raise GitTruckError(f"git-truck never printed port within {_PORT_WAIT_TIMEOUT_S}s")


def _read_output(proc: subprocess.Popen, output: queue.Queue) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        output.put(line)
    output.put(None)


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


def _wait_for_completion(repo_abs: str, branch: str, deadline: float, cache_root: Path) -> None:
    key = f"{repo_abs}---{branch}"
    metadata = cache_root / "metadata.json"
    while time.monotonic() < deadline:
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
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=_SIGTERM_GRACE_S)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=2)


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
    with tempfile.TemporaryDirectory(prefix="diligence-git-truck-") as temp:
        cache_root = Path(temp) / "git-truck-cache"
        db_path = _db_path(repo_abs, branch, cache_root)
        proc = subprocess.Popen(
            ["npx", "-y", f"git-truck@{GIT_TRUCK_VERSION}", "--headless"],
            cwd=repo_abs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            env={**os.environ, "HOST": "127.0.0.1", "TMPDIR": temp, "TMP": temp, "TEMP": temp},
            start_new_session=True,
        )
        output: queue.Queue = queue.Queue()
        reader = threading.Thread(target=_read_output, args=(proc, output), daemon=True)
        reader.start()
        view = None
        log = []
        try:
            port = _wait_for_port(proc, time.monotonic() + _PORT_WAIT_TIMEOUT_S, log, output)
            view = _kick_view(port)
            _wait_for_completion(repo_abs, branch, time.monotonic() + _ANALYSIS_TIMEOUT_S, cache_root)
        finally:
            _terminate(proc)
            reader.join(timeout=_SIGTERM_GRACE_S)
            if view is not None:
                view.join(timeout=_SIGTERM_GRACE_S)
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
