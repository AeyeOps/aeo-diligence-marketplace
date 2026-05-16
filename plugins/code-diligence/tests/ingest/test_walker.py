import subprocess
from pathlib import Path

from code_diligence.ingest.walker import walk_commits


def test_walks_synthetic_api_repo(synthetic_target: Path) -> None:
    commits = list(walk_commits(synthetic_target / "api"))
    assert len(commits) == 6
    shas = [c.sha for c in commits]
    assert len(set(shas)) == 6
    emails = {c.author_email for c in commits}
    assert "pat@acme.com" in emails
    assert "pat@gmail.com" in emails
    assert "mike@acme.com" in emails


def test_walks_yields_file_changes(synthetic_target: Path) -> None:
    commits = list(walk_commits(synthetic_target / "api"))
    bootstrap = next(c for c in commits if c.message_first_line.startswith("feat: bootstrap"))
    assert any(fc.path == "main.py" and fc.lines_added > 0 for fc in bootstrap.file_changes)


def test_handles_empty_repo(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=repo, check=True)
    commits = list(walk_commits(repo))
    assert commits == []


def test_persist_writes_commit_file_authors(synthetic_target: Path, tmp_path: Path) -> None:
    """75b: persist_repo_git_facts writes per-(commit, file, author) edges."""
    from code_diligence.ingest.persist import persist_repo_git_facts
    from code_diligence.warehouse.connection import open_warehouse
    from code_diligence.warehouse.migrations import migrate
    from code_diligence.warehouse.repos import upsert_repo
    from code_diligence.warehouse.targets import register_target

    db = tmp_path / "wh.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(
            conn, repo_id="acme/api", target_id="acme",
            name="api", source_url=str(synthetic_target / "api"),
        )
        persist_repo_git_facts(
            conn, repo_id="acme/api",
            commits=walk_commits(synthetic_target / "api"),
        )
        n_edges = conn.execute(
            "SELECT COUNT(*) FROM commit_file_authors WHERE repo_id='acme/api'"
        ).fetchone()[0]
        distinct_files = conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM commit_file_authors WHERE repo_id='acme/api'"
        ).fetchone()[0]
    assert n_edges >= 6, f"expected per-file edges, got {n_edges}"
    assert distinct_files >= 1
