import subprocess
from pathlib import Path

import pytest

from code_diligence.curation.orchestrate import run_curation_pass
from code_diligence.curation.schema import (
    IdentityMergeEntry,
    IdentityMergesFile,
    RepoClassificationFile,
)
from code_diligence.ingest.persist import persist_repo_git_facts
from code_diligence.ingest.walker import walk_commits
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


@pytest.fixture
def populated_warehouse(tmp_path: Path, synthetic_target: Path) -> tuple[Path, Path, Path]:
    """Returns (warehouse_path, repo_root, curation_dir).

    Pre-clones synthetic repos under repo_root and persists git facts to a
    fresh warehouse, just like the CLI quick path does.
    """
    warehouse = tmp_path / "acme.duckdb"
    repo_root = tmp_path / "repos"
    curation = tmp_path / "curation"
    repo_root.mkdir(parents=True)
    for r in synthetic_target.iterdir():
        subprocess.run(
            ["git", "clone", "--quiet", str(r), str(repo_root / r.name)],
            check=True,
        )
    with open_warehouse(warehouse) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        for repo_dir in sorted(repo_root.iterdir()):
            if not (repo_dir / ".git").is_dir():
                continue
            repo_id = f"acme/{repo_dir.name}"
            upsert_repo(
                conn, repo_id=repo_id, target_id="acme",
                name=repo_dir.name, source_url=str(repo_dir),
            )
            persist_repo_git_facts(
                conn, repo_id=repo_id, commits=walk_commits(repo_dir),
            )
    return warehouse, repo_root, curation


def test_first_run_produces_yaml_and_warehouse_rows(populated_warehouse: tuple[Path, Path, Path]) -> None:
    warehouse, repo_root, curation = populated_warehouse
    with open_warehouse(warehouse) as conn:
        run_curation_pass(
            conn, target_id="acme", target_domain="acme.com",
            curation_dir=curation, repo_root=repo_root,
            abandoned_threshold_days=180,
        )
        # Identity table populated
        n_id = conn.execute(
            "SELECT COUNT(*) FROM identity_map WHERE target_id='acme'"
        ).fetchone()[0]
        # Repo classification populated
        n_rc = conn.execute("SELECT COUNT(*) FROM repo_classification").fetchone()[0]
    assert (curation / "identity-merges.yaml").exists()
    assert (curation / "fte-classification.yaml").exists()
    assert (curation / "repo-classification.yaml").exists()
    assert n_id >= 1
    assert n_rc >= 1
    # FTE classification YAML must list at least one author (synthetic has multiple)
    from code_diligence.curation.schema import FteClassificationFile
    fte_parsed = FteClassificationFile.from_yaml(
        (curation / "fte-classification.yaml").read_text()
    )
    assert len(fte_parsed.confirmed) + len(fte_parsed.needs_review) >= 1


def test_pat_aliases_merged(populated_warehouse: tuple[Path, Path, Path]) -> None:
    warehouse, repo_root, curation = populated_warehouse
    with open_warehouse(warehouse) as conn:
        run_curation_pass(
            conn, target_id="acme", target_domain="acme.com",
            curation_dir=curation, repo_root=repo_root,
            abandoned_threshold_days=180,
        )
    text = (curation / "identity-merges.yaml").read_text()
    parsed = IdentityMergesFile.from_yaml(text)
    # Two Pats: same name "Pat Smith" on two emails — the heuristic scores
    # high-confidence so the pair lands in confirmed (or needs_review on a
    # threshold change). Either bucket counts.
    all_entries = parsed.confirmed + parsed.needs_review
    pairs = {(e.canonical, e.alias) for e in all_entries} | {
        (e.alias, e.canonical) for e in all_entries
    }
    assert ("pat@acme.com", "pat@gmail.com") in pairs or \
           ("pat@gmail.com", "pat@acme.com") in pairs


def test_legacy_old_classified_as_abandoned(populated_warehouse: tuple[Path, Path, Path]) -> None:
    warehouse, repo_root, curation = populated_warehouse
    with open_warehouse(warehouse) as conn:
        run_curation_pass(
            conn, target_id="acme", target_domain="acme.com",
            curation_dir=curation, repo_root=repo_root,
            abandoned_threshold_days=180,
        )
    parsed = RepoClassificationFile.from_yaml(
        (curation / "repo-classification.yaml").read_text()
    )
    all_entries = parsed.confirmed + parsed.needs_review
    by_id = {e.repo_id: e for e in all_entries}
    assert by_id["acme/legacy-old"].label == "abandoned"


def test_vendored_lib_classified_as_fork(populated_warehouse: tuple[Path, Path, Path]) -> None:
    warehouse, repo_root, curation = populated_warehouse
    with open_warehouse(warehouse) as conn:
        run_curation_pass(
            conn, target_id="acme", target_domain="acme.com",
            curation_dir=curation, repo_root=repo_root,
            abandoned_threshold_days=180,
        )
    parsed = RepoClassificationFile.from_yaml(
        (curation / "repo-classification.yaml").read_text()
    )
    all_entries = parsed.confirmed + parsed.needs_review
    by_id = {e.repo_id: e for e in all_entries}
    assert by_id["acme/vendored-lib"].label == "fork"


def test_do_not_merge_persists_across_runs(populated_warehouse: tuple[Path, Path, Path]) -> None:
    warehouse, repo_root, curation = populated_warehouse
    with open_warehouse(warehouse) as conn:
        run_curation_pass(
            conn, target_id="acme", target_domain="acme.com",
            curation_dir=curation, repo_root=repo_root,
            abandoned_threshold_days=180,
        )

    # Simulate analyst edit: add a do_not_merge entry and clear confirmed
    id_path = curation / "identity-merges.yaml"
    edited = IdentityMergesFile(
        confirmed=[],
        needs_review=[],
        do_not_merge=[IdentityMergeEntry(
            canonical="pat@acme.com", alias="pat@gmail.com",
            source="analyst", confidence=1.0,
        )],
    )
    id_path.write_text(edited.to_yaml())

    with open_warehouse(warehouse) as conn:
        run_curation_pass(
            conn, target_id="acme", target_domain="acme.com",
            curation_dir=curation, repo_root=repo_root,
            abandoned_threshold_days=180,
        )

    parsed = IdentityMergesFile.from_yaml(id_path.read_text())
    # Analyst do_not_merge persists; heuristic does not re-confirm the pair
    assert len(parsed.do_not_merge) == 1
    assert parsed.do_not_merge[0].source == "analyst"
    confirmed_pairs = {(e.canonical, e.alias) for e in parsed.confirmed}
    assert ("pat@acme.com", "pat@gmail.com") not in confirmed_pairs
    assert ("pat@gmail.com", "pat@acme.com") not in confirmed_pairs
