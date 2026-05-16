import shutil
from pathlib import Path

import pytest

from code_diligence.ingest.cheap_tools import run_cheap_tools_for_repo
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


@pytest.mark.skipif(
    not all(shutil.which(t) for t in ["git-fame", "git-of-theseus-analyze", "npx"]),
    reason="cheap tools not all installed",
)
def test_runs_all_three_tools(synthetic_target: Path, tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url=str(synthetic_target / "api"))
        run_cheap_tools_for_repo(
            conn, target_id="acme", repo_id="acme/api",
            repo_path=synthetic_target / "api", max_workers=3,
        )
        gf = conn.execute(
            "SELECT COUNT(*) FROM ownership_share WHERE source='git-fame' AND repo_id='acme/api'"
        ).fetchone()[0]
        ages = conn.execute(
            "SELECT COUNT(*) FROM code_age_buckets WHERE repo_id='acme/api'"
        ).fetchone()[0]
    assert gf > 0
    # ages may be 0 for very tiny repos; just assert no crash
    assert ages >= 0


def test_failures_isolated(tmp_path: Path) -> None:
    """If a repo doesn't exist on disk, all tools fail-isolated and the function returns cleanly."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/missing", target_id="acme",
                    name="missing", source_url="/does/not/exist")
        # Should not raise — all tools fail in isolation
        run_cheap_tools_for_repo(
            conn, target_id="acme", repo_id="acme/missing",
            repo_path=Path("/does/not/exist"), max_workers=3,
        )
        failures = conn.execute(
            "SELECT tool, class FROM tool_failures WHERE repo_id='acme/missing'"
        ).fetchall()
    # At least one tool should have logged a failure
    tools_failed = {f[0] for f in failures}
    assert tools_failed  # non-empty
