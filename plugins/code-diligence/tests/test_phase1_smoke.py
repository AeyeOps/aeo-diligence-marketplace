"""Phase 1 acceptance: full quick-tier pipeline against synthetic target produces a dashboard."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from code_diligence.warehouse.connection import open_warehouse


REQUIRED_TOOLS = ["git", "uv", "npm"]
OPTIONAL_TOOLS = ["git-fame", "git-of-theseus-analyze", "npx", "claude"]


@pytest.mark.skipif(
    not all(shutil.which(t) for t in REQUIRED_TOOLS),
    reason=f"requires {REQUIRED_TOOLS} on PATH",
)
def test_phase1_quick_ingest_to_dashboard(synthetic_target: Path, tmp_path: Path) -> None:
    # 1. Set up settings file pointing at synthetic target
    warehouse = tmp_path / "smoke.duckdb"
    repo_root = tmp_path / "repos"
    curation = tmp_path / "curation"
    output = tmp_path / "dashboard"
    settings = tmp_path / "code-diligence-smoke.local.md"
    settings.write_text(f"""---
target_id: smoke
target_name: Smoke Test
description: end-to-end Phase 1 smoke
---
sources:
  github:
    enabled: false
storage:
  warehouse_path: {warehouse}
  repo_clone_root: {repo_root}
  curation_dir: {curation}
dashboard:
  theme: default
  output_path: {output}
""")

    # 2. Pre-clone synthetic repos into repo_clone_root (production deployment uses GitHub clone)
    repo_root.mkdir()
    for r in synthetic_target.iterdir():
        subprocess.run(["git", "clone", "--quiet", str(r), str(repo_root / r.name)], check=True)

    # 3. Run ingest --quick
    r = subprocess.run(
        ["uv", "run", "code-diligence", "ingest", str(settings), "--quick"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"ingest failed:\nstdout:{r.stdout}\nstderr:{r.stderr}"

    # 4. Assert warehouse populated
    with open_warehouse(warehouse) as conn:
        n_commits = conn.execute("SELECT COUNT(*) FROM commits_fact").fetchone()[0]
        n_repos = conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
        n_targets = conn.execute("SELECT COUNT(*) FROM targets").fetchone()[0]
    assert n_targets == 1
    assert n_repos == 6
    assert n_commits >= 14

    # 5. Curation YAMLs written
    assert (curation / "identity-merges.yaml").exists()
    assert (curation / "fte-classification.yaml").exists()
    assert (curation / "repo-classification.yaml").exists()

    # Pat aliasing should be auto-merged
    id_yaml = (curation / "identity-merges.yaml").read_text()
    assert "pat@acme.com" in id_yaml and "pat@gmail.com" in id_yaml

    # legacy-old should be classified abandoned
    rc_yaml = (curation / "repo-classification.yaml").read_text()
    assert "abandoned" in rc_yaml

    # 6. Render dashboard
    r2 = subprocess.run(
        ["uv", "run", "python", "-m", "code_diligence.dashboard.render",
         "--warehouse", str(warehouse), "--output", str(output)],
        capture_output=True, text=True,
    )
    assert r2.returncode == 0, f"dashboard render failed:\nstdout:{r2.stdout}\nstderr:{r2.stderr}"

    # 7. Assert dashboard built
    assert (output / "index.html").exists()
    html = (output / "index.html").read_text()
    assert "code-diligence" in html.lower()
