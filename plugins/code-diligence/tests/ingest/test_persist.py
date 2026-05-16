from pathlib import Path

from code_diligence.ingest.persist import persist_repo_git_facts
from code_diligence.ingest.walker import walk_commits
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


def _setup_acme(synthetic_target: Path, db_path: Path) -> None:
    with open_warehouse(db_path) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        for repo_dir in sorted(synthetic_target.iterdir()):
            upsert_repo(
                conn, repo_id=f"acme/{repo_dir.name}", target_id="acme",
                name=repo_dir.name, source_url=str(repo_dir),
            )


def test_persist_populates_commits_authors_file_metrics(
    synthetic_target: Path, tmp_path: Path
) -> None:
    db = tmp_path / "test.duckdb"
    _setup_acme(synthetic_target, db)
    api = synthetic_target / "api"
    commits = list(walk_commits(api))
    with open_warehouse(db) as conn:
        persist_repo_git_facts(conn, repo_id="acme/api", commits=commits)
        n_commits = conn.execute(
            "SELECT COUNT(*) FROM commits_fact WHERE repo_id='acme/api'"
        ).fetchone()[0]
        n_authors = conn.execute(
            "SELECT COUNT(*) FROM authors WHERE target_id='acme'"
        ).fetchone()[0]
        n_files = conn.execute(
            "SELECT COUNT(*) FROM file_metrics WHERE repo_id='acme/api'"
        ).fetchone()[0]
        repo_meta = conn.execute(
            "SELECT first_commit_at, last_commit_at FROM repos WHERE repo_id='acme/api'"
        ).fetchone()
    assert n_commits == 6
    assert n_authors == 3
    assert n_files >= 4
    assert repo_meta[0] is not None and repo_meta[1] is not None


def test_persist_idempotent(synthetic_target: Path, tmp_path: Path) -> None:
    db = tmp_path / "test.duckdb"
    _setup_acme(synthetic_target, db)
    api = synthetic_target / "api"
    with open_warehouse(db) as conn:
        for _ in range(2):
            commits = list(walk_commits(api))
            persist_repo_git_facts(conn, repo_id="acme/api", commits=commits)
        n_commits = conn.execute(
            "SELECT COUNT(*) FROM commits_fact WHERE repo_id='acme/api'"
        ).fetchone()[0]
    assert n_commits == 6
