"""Shared pytest fixtures."""
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent
FIXTURE_BUILDER = PLUGIN_ROOT / "fixtures" / "build_synthetic_target.sh"


@pytest.fixture
def synthetic_target(tmp_path: Path) -> Path:
    """Build a fresh synthetic target into tmp_path/target. Returns the target dir."""
    if not shutil.which("git"):
        pytest.skip("git not on PATH")
    out = tmp_path / "target"
    subprocess.run(
        ["bash", str(FIXTURE_BUILDER), str(out)],
        check=True, capture_output=True,
    )
    return out
