"""Clone-or-fetch a remote git repo to a local path. Idempotent."""
import subprocess
from pathlib import Path


class CloneError(RuntimeError):
    """Raised when git clone or fetch fails."""


def clone_or_fetch(*, source_url: str, dest: Path) -> str:
    """Clone source_url to dest if dest is empty; otherwise fetch into existing repo.

    Returns the HEAD commit SHA after the operation.

    Raises CloneError on subprocess failure.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if (dest / ".git").is_dir():
        _run(["git", "-C", str(dest), "fetch", "--all", "--tags", "--prune", "--quiet"])
    else:
        _run(["git", "clone", "--quiet", source_url, str(dest)])
    return _run(["git", "-C", str(dest), "rev-parse", "HEAD"]).strip()


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CloneError(f"{' '.join(cmd)} failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout
