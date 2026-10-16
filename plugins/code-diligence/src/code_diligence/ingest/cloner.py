"""Clone a source or fast-forward an existing local checkout."""
import base64
import os
import subprocess
from pathlib import Path


class CloneError(RuntimeError):
    """Raised when a source cannot be cloned or fast-forwarded."""


def clone_or_fetch(*, source_url: str, dest: Path, token: str | None = None) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    if token is not None:
        index = int(env.get("GIT_CONFIG_COUNT", "0"))
        env["GIT_CONFIG_COUNT"] = str(index + 1)
        env[f"GIT_CONFIG_KEY_{index}"] = "http.https://github.com/.extraheader"
        credential = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env[f"GIT_CONFIG_VALUE_{index}"] = f"Authorization: Basic {credential}"
    if (dest / ".git").exists():
        _run(["git", "-C", str(dest), "fetch", "origin", "--tags", "--prune", "--quiet"], env)
        _run(["git", "-C", str(dest), "merge", "--ff-only", "@{upstream}"], env)
    else:
        _run(["git", "clone", "--quiet", "--", source_url, str(dest)], env)
    return _run(["git", "-C", str(dest), "rev-parse", "HEAD"], env).strip()


def _run(cmd: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise CloneError(f"git operation failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout
