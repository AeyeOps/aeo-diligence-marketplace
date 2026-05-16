import shutil
from pathlib import Path

import pytest

from code_diligence.tools.git_fame import GitFameRecord, persist_git_fame, run_git_fame
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


@pytest.mark.skipif(not shutil.which("git-fame"), reason="git-fame not installed")
def test_run_git_fame_returns_records(synthetic_target: Path) -> None:
    records = run_git_fame(synthetic_target / "api")
    assert len(records) >= 2
    assert all(isinstance(r, GitFameRecord) for r in records)
    emails = {r.author_email for r in records}
    assert "pat@acme.com" in emails or "Pat Smith" in {r.author_name for r in records}


@pytest.mark.skipif(not shutil.which("git-fame"), reason="git-fame not installed")
def test_persist_git_fame_writes_ownership_share(synthetic_target: Path, tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url=str(synthetic_target / "api"))
        records = run_git_fame(synthetic_target / "api")
        persist_git_fame(conn, repo_id="acme/api", records=records)
        rows = conn.execute(
            "SELECT author_email, owned_loc, owned_files FROM ownership_share "
            "WHERE repo_id='acme/api' AND source='git-fame'"
        ).fetchall()
    assert len(rows) >= 2
    assert sum(r[1] for r in rows) > 0  # some LOC attributed


def test_parse_git_fame_json_fixture() -> None:
    """Pure parser test — works without git-fame installed."""
    from code_diligence.tools.git_fame import parse_git_fame_json
    sample = {
        "data": [
            ["Pat S", "pat@acme.com", "30", "5", "3", "0.5"],
            ["Mike B", "mike@acme.com", "10", "2", "1", "0.2"],
        ],
        "columns": ["Author", "Email", "loc", "coms", "fils", "distribution"],
    }
    records = parse_git_fame_json(sample)
    assert len(records) == 2
    assert records[0].author_email == "pat@acme.com"
    assert records[0].owned_loc == 30
    assert records[0].owned_files == 3
