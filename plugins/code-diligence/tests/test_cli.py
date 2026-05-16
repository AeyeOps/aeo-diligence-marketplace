import os
import shutil
import subprocess
from pathlib import Path

import pytest

from code_diligence.warehouse.connection import open_warehouse


@pytest.fixture
def settings_file(tmp_path: Path, synthetic_target: Path) -> Path:
    """Write a TargetSettings .local.md pointing at the synthetic target."""
    warehouse = tmp_path / "acme.duckdb"
    repos_root = tmp_path / "repos"
    curation = tmp_path / "curation"
    f = tmp_path / "code-diligence-acme.local.md"
    f.write_text(f"""---
target_id: acme
target_name: Acme
description: synthetic
---
sources:
  github:
    enabled: false
storage:
  warehouse_path: {warehouse}
  repo_clone_root: {repos_root}
  curation_dir: {curation}
""")
    # Pre-clone the synthetic target into the expected repo_clone_root so the
    # CLI's "clone" step finds local sources to copy from.
    repos_root.mkdir(parents=True)
    for r in synthetic_target.iterdir():
        subprocess.run(["git", "clone", "--quiet", str(r), str(repos_root / r.name)], check=True)
    return f


def test_cli_ingest_quick_populates_warehouse(settings_file: Path, tmp_path: Path) -> None:
    result = subprocess.run(
        ["uv", "run", "code-diligence", "ingest", str(settings_file), "--quick"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    warehouse = tmp_path / "acme.duckdb"
    assert warehouse.exists()
    with open_warehouse(warehouse) as conn:
        n_commits = conn.execute("SELECT COUNT(*) FROM commits_fact").fetchone()[0]
        n_repos = conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
    assert n_commits >= 14  # synthetic has ~16 commits across all repos
    assert n_repos == 6  # six synthetic repos

    # Curation outputs land beside the settings file (curation_dir in settings)
    curation = settings_file.parent / "curation"
    identity_yaml = curation / "identity-merges.yaml"
    fte_yaml = curation / "fte-classification.yaml"
    repo_yaml = curation / "repo-classification.yaml"
    assert identity_yaml.exists()
    assert fte_yaml.exists()
    assert repo_yaml.exists()

    # Both pat emails referenced in the identity file (confirmed or needs_review)
    id_content = identity_yaml.read_text()
    assert "pat@acme.com" in id_content
    assert "pat@gmail.com" in id_content

    # legacy-old should be classified abandoned
    assert "abandoned" in repo_yaml.read_text()

    import shutil
    if all(shutil.which(t) for t in ["git-fame", "git-of-theseus-analyze", "npx"]):
        with open_warehouse(warehouse) as conn:
            n_ownership = conn.execute("SELECT COUNT(*) FROM ownership_share").fetchone()[0]
            n_ages = conn.execute("SELECT COUNT(*) FROM code_age_buckets").fetchone()[0]
        assert n_ownership > 0
        # n_ages >= 0 — small synthetic repos may produce no buckets

    if shutil.which("claude") and os.environ.get("ANTHROPIC_API_KEY"):
        with open_warehouse(warehouse) as conn:
            n_narratives = conn.execute("SELECT COUNT(*) FROM narratives WHERE target_id='acme'").fetchone()[0]
        assert n_narratives == 16


def test_cli_ingest_quick_populates_tooling_versions(
    settings_file: Path, tmp_path: Path
) -> None:
    """75a: targets.tooling_versions is non-empty JSON after a quick-tier ingest."""
    import json
    result = subprocess.run(
        ["uv", "run", "code-diligence", "ingest", str(settings_file), "--quick"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    warehouse = tmp_path / "acme.duckdb"
    with open_warehouse(warehouse) as conn:
        row = conn.execute(
            "SELECT tooling_versions FROM targets WHERE target_id = 'acme'"
        ).fetchone()
    assert row is not None and row[0], "tooling_versions must be populated after ingest"
    versions = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    assert isinstance(versions, dict) and len(versions) >= 1
    assert "code-diligence-walker" in versions


@pytest.mark.skipif(
    not (shutil.which("java") and shutil.which("hercules") and shutil.which("repowise")),
    reason="java, hercules, and repowise must all be installed for full-tier test",
)
def test_cli_ingest_full_completes(settings_file: Path, tmp_path: Path) -> None:
    result = subprocess.run(
        ["uv", "run", "code-diligence", "ingest", str(settings_file), "--full"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    warehouse = tmp_path / "acme.duckdb"
    assert warehouse.exists()
