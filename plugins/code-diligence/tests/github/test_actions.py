import pytest
from pathlib import Path
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.github.actions import fetch_and_persist_actions


def test_fetch_and_persist_actions(httpx_mock, tmp_path: Path) -> None:
    httpx_mock.add_response(
        url="https://api.github.com/repos/acme/api/actions/runs?per_page=100&page=1",
        json=[{
            "id": 42,
            "name": "CI",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:10:00Z",
            "conclusion": "success",
        }],
        headers={},
    )

    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url="https://github.com/acme/api")
        fetch_and_persist_actions(conn, repo_id="acme/api", token="test", repo_full_name="acme/api")
        rows = conn.execute("SELECT run_id, workflow_name, conclusion, duration_seconds FROM actions_metrics").fetchall()

    assert len(rows) == 1
    assert rows[0][0] == 42
    assert rows[0][1] == "CI"
    assert rows[0][2] == "success"
    assert rows[0][3] == pytest.approx(600.0)
