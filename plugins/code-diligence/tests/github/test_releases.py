import pytest
from pathlib import Path
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.github.releases import fetch_and_persist_releases


def test_fetch_and_persist_releases(httpx_mock, tmp_path: Path) -> None:
    httpx_mock.add_response(
        url="https://api.github.com/repos/acme/api/releases?per_page=100&page=1",
        json=[
            {"tag_name": "v1.0.0", "published_at": "2026-01-01T00:00:00Z"},
            {"tag_name": "v1.1.0", "published_at": "2026-02-01T00:00:00Z"},
        ],
        headers={},
    )

    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url="https://github.com/acme/api")
        fetch_and_persist_releases(conn, repo_id="acme/api", token="test", repo_full_name="acme/api")
        rows = conn.execute("SELECT tag, days_since_prev FROM release_metrics ORDER BY released_at").fetchall()

    assert len(rows) == 2
    assert rows[0][0] == "v1.0.0"
    assert rows[0][1] is None  # first release has no previous
    assert rows[1][0] == "v1.1.0"
    assert rows[1][1] == pytest.approx(31.0)
