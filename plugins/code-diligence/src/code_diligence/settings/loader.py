"""Load TargetSettings from a .local.md file with YAML frontmatter + body."""
import os
import re
from pathlib import Path
from typing import Any

import yaml

from .schema import TargetSettings

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def load_target_settings(path: Path) -> TargetSettings:
    """Parse a target settings file. Frontmatter has identity; body has config."""
    text = path.read_text()
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(
            f"settings file {path} is missing YAML frontmatter "
            "(must start with '---\\n...\\n---\\n')"
        )
    frontmatter = yaml.safe_load(m.group(1)) or {}
    body = yaml.safe_load(m.group(2)) or {}
    merged: dict[str, Any] = {**frontmatter, **body}
    return TargetSettings.model_validate(merged)


def resolve_token(env_var: str) -> str:
    """Read a token from an env var. Raises if missing or empty."""
    value = os.environ.get(env_var, "").strip()
    if not value:
        raise RuntimeError(
            f"required env var {env_var} is not set or is empty; "
            "set it before running the ingest pipeline"
        )
    return value
