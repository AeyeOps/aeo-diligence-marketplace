import pytest
from pathlib import Path
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.github.pulls import fetch_and_persist_prs


def test_fetch_and_persist_prs(httpx_mock, tmp_path: Path) -> None:
    httpx_mock.add_response(
        url="https://api.github.com/repos/acme/api/pulls?per_page=100&state=all&page=1",
        json=[{
            "number": 1, "created_at": "2026-01-01T00:00:00Z",
            "merged_at": "2026-01-02T00:00:00Z", "closed_at": "2026-01-02T00:00:00Z",
            "additions": 50, "deletions": 5, "user": {"login": "pat"},
            "merged_by": {"login": "pat"},
            "requested_reviewers": [],
        }],
        headers={},
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/acme/api/pulls/1/reviews?per_page=100&page=1",
        json=[{"state": "APPROVED", "user": {"login": "mike"}, "submitted_at": "2026-01-01T12:00:00Z"}],
        headers={},
    )

    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url="https://github.com/acme/api")
        fetch_and_persist_prs(conn, repo_id="acme/api", token="test", repo_full_name="acme/api")
        rows = conn.execute("SELECT pr_number, num_reviewers, was_self_merged, review_latency_hours FROM pr_metrics").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 1
    assert rows[0][1] == 1  # one reviewer (mike)
    assert rows[0][2] is True  # author == merger
    assert rows[0][3] is not None and rows[0][3] >= 0
