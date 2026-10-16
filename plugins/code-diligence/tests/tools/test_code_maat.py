import shutil
from pathlib import Path

import pytest

from code_diligence.ingest.persist import persist_repo_git_facts
from code_diligence.ingest.walker import walk_commits
from code_diligence.tools.code_maat import (
    CODE_MAAT_JAR,
    build_log_dump,
    parse_revisions_csv,
    persist_revisions,
    run_code_maat_analysis,
)
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


def test_parse_revisions_csv() -> None:
    sample = "entity,n-revs\napi/main.py,5\napi/auth.py,3\n"
    rows = parse_revisions_csv(sample)
    assert rows == [("api/main.py", 5), ("api/auth.py", 3)]


@pytest.mark.skipif(not shutil.which("java"), reason="java not installed")
@pytest.mark.skipif(not CODE_MAAT_JAR.exists(), reason="code-maat JAR not vendored")
def test_build_log_dump_then_run_revisions(synthetic_target: Path, tmp_path: Path) -> None:
    log_dump = build_log_dump(synthetic_target / "api", out=tmp_path / "log.txt")
    assert log_dump.exists()
    csv_text = run_code_maat_analysis(log_dump, analysis="revisions")
    assert "entity" in csv_text and "n-revs" in csv_text


@pytest.mark.skipif(not shutil.which("java"), reason="java not installed")
@pytest.mark.skipif(not CODE_MAAT_JAR.exists(), reason="code-maat JAR not vendored")
def test_persist_revisions_into_warehouse(synthetic_target: Path, tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url=str(synthetic_target / "api"))
        persist_repo_git_facts(conn, repo_id="acme/api", commits=walk_commits(synthetic_target / "api"))
        log_dump = build_log_dump(synthetic_target / "api", out=tmp_path / "log.txt")
        csv_text = run_code_maat_analysis(log_dump, analysis="revisions")
        persist_revisions(conn, repo_id="acme/api", csv_text=csv_text)
        n = conn.execute("SELECT COUNT(*) FROM file_metrics WHERE repo_id='acme/api'").fetchone()[0]
    assert n > 0
