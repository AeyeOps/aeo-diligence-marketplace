import pytest
from pathlib import Path
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.github.issues import fetch_and_persist_issues


def test_fetch_and_persist_issues(httpx_mock, tmp_path: Path) -> None:
    # Issues list (no pull_request key → real issue)
    httpx_mock.add_response(
        url="https://api.github.com/repos/acme/api/issues?per_page=100&state=all&filter=all&page=1",
        json=[{
            "number": 5,
            "created_at": "2026-01-01T00:00:00Z",
            "closed_at": "2026-01-10T00:00:00Z",
            "state": "closed",
            "labels": [{"name": "bug"}],
        }],
        headers={},
    )
    # Comments for issue #5
    httpx_mock.add_response(
        url="https://api.github.com/repos/acme/api/issues/5/comments?per_page=100&page=1",
        json=[{"created_at": "2026-01-02T00:00:00Z", "body": "Looking into this."}],
        headers={},
    )

    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url="https://github.com/acme/api")
        fetch_and_persist_issues(conn, repo_id="acme/api", token="test", repo_full_name="acme/api")
        rows = conn.execute(
            "SELECT issue_number, state, days_to_first_response FROM issue_metrics"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0][0] == 5
    assert rows[0][1] == "closed"
    assert rows[0][2] == pytest.approx(1.0)


def test_pr_rows_are_skipped(httpx_mock, tmp_path: Path) -> None:
    """Issues with pull_request key must be filtered out."""
    httpx_mock.add_response(
        url="https://api.github.com/repos/acme/api/issues?per_page=100&state=all&filter=all&page=1",
        json=[{
            "number": 10,
            "created_at": "2026-01-01T00:00:00Z",
            "closed_at": None,
            "state": "open",
            "labels": [],
            "pull_request": {"url": "https://api.github.com/repos/acme/api/pulls/10"},
        }],
        headers={},
    )

    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url="https://github.com/acme/api")
        fetch_and_persist_issues(conn, repo_id="acme/api", token="test", repo_full_name="acme/api")
        rows = conn.execute("SELECT issue_number FROM issue_metrics").fetchall()

    assert rows == []
