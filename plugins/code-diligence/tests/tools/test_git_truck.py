import shutil
from pathlib import Path

import pytest

from code_diligence.tools.git_truck import (
    GitTruckOwnership,
    _sanitize,
    persist_git_truck,
    run_git_truck,
)
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


_HAS_NPX = shutil.which("npx") is not None


def test_sanitize_matches_git_truck_v3_path_rules() -> None:
    """Regression would silently break cache-path lookup against v3's on-disk layout."""
    assert _sanitize("/private/var/foo") == "_private_var_foo_"
    assert _sanitize("main") == "main_"
    assert _sanitize("feat/branch-1") == "feat_branch_1_"
    assert _sanitize("/") == "__"
    assert _sanitize("abc123") == "abc123_"


@pytest.mark.skipif(not _HAS_NPX, reason="npx not on PATH (Node 20+ required)")
def test_run_git_truck_returns_records(synthetic_target: Path) -> None:
    """End-to-end: drive git-truck v3 against the synthetic api repo and verify
    we extract per-author dominant-file ownership from its DuckDB cache."""
    records = run_git_truck(synthetic_target / "api")
    assert records, "expected at least one ownership record from the synthetic api repo"
    assert all(isinstance(r, GitTruckOwnership) for r in records)
    assert all(r.owned_files >= 1 for r in records)
    assert all(r.owned_loc >= 0 for r in records)


@pytest.mark.skipif(not _HAS_NPX, reason="npx not on PATH (Node 20+ required)")
def test_run_git_truck_persists_through_full_pipeline(
    synthetic_target: Path, tmp_path: Path,
) -> None:
    """End-to-end ingest: run_git_truck → persist_git_truck → ownership_share."""
    records = run_git_truck(synthetic_target / "api")
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url="local")
        persist_git_truck(conn, repo_id="acme/api", records=records)
        count = conn.execute(
            "SELECT COUNT(*) FROM ownership_share "
            "WHERE repo_id='acme/api' AND source='git-truck'"
        ).fetchone()[0]
    assert count == len(records)


def test_persist_git_truck_writes_ownership_share(tmp_path: Path) -> None:
    """Pure DB test — exercises persist with synthetic records, no subprocess."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url="local")
        persist_git_truck(conn, repo_id="acme/api", records=[
            GitTruckOwnership(author_name="Pat S", author_email=None,
                              owned_loc=1500, owned_files=2),
            GitTruckOwnership(author_name="Mike B", author_email=None,
                              owned_loc=500, owned_files=2),
        ])
        rows = conn.execute(
            "SELECT author_email, owned_loc, owned_files FROM ownership_share "
            "WHERE repo_id='acme/api' AND source='git-truck' ORDER BY author_email"
        ).fetchall()
    assert len(rows) == 2
    emails = {r[0] for r in rows}
    assert any("pat" in e for e in emails)
    assert any("mike" in e for e in emails)


def test_persist_git_truck_replaces_existing_rows(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url="local")
        persist_git_truck(conn, repo_id="acme/api", records=[
            GitTruckOwnership(author_name="A", author_email=None, owned_loc=100, owned_files=1),
        ])
        persist_git_truck(conn, repo_id="acme/api", records=[
            GitTruckOwnership(author_name="B", author_email=None, owned_loc=50, owned_files=1),
        ])
        rows = conn.execute(
            "SELECT author_email FROM ownership_share "
            "WHERE repo_id='acme/api' AND source='git-truck'"
        ).fetchall()
    assert len(rows) == 1
    assert "b" in rows[0][0]


def test_persist_git_truck_empty_records_clears_existing(tmp_path: Path) -> None:
    """An empty records list should still wipe any prior git-truck rows."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url="local")
        persist_git_truck(conn, repo_id="acme/api", records=[
            GitTruckOwnership(author_name="A", author_email=None, owned_loc=10, owned_files=1),
        ])
        persist_git_truck(conn, repo_id="acme/api", records=[])
        count = conn.execute(
            "SELECT COUNT(*) FROM ownership_share "
            "WHERE repo_id='acme/api' AND source='git-truck'"
        ).fetchone()[0]
    assert count == 0
