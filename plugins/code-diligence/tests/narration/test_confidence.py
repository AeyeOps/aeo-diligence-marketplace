"""Tests for compute_axis_confidence."""
from pathlib import Path

from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.narration.confidence import compute_axis_confidence


def _setup_base(conn, target_id: str, repo_id: str) -> None:
    migrate(conn)
    register_target(conn, target_id=target_id, name="Acme")
    upsert_repo(conn, repo_id=repo_id, target_id=target_id, name="api", source_url="/tmp/api")


def test_all_axes_low_with_only_commits(tmp_path: Path) -> None:
    """With only commits_fact populated, people=low, product=low, process=low."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        _setup_base(conn, "acme", "acme/api")
        # Insert one commit row so commits_fact is populated
        conn.execute(
            "INSERT INTO commits_fact (repo_id, commit_sha, author_email, author_date) "
            "VALUES ('acme/api', 'abc123', 'dev@acme.com', '2024-01-01')"
        )
        compute_axis_confidence(conn, target_id="acme")
        rows = conn.execute(
            "SELECT axis, confidence_class, signal_completeness_pct FROM axis_confidence "
            "WHERE target_id='acme' ORDER BY axis"
        ).fetchall()
    by_axis = {r[0]: (r[1], r[2]) for r in rows}
    assert set(by_axis.keys()) == {"people", "product", "process"}
    # commits_fact populated → 1/3 for people → medium threshold is 0.4 → low (33%)
    assert by_axis["people"][0] == "low"
    # process: nothing populated → low
    assert by_axis["process"][0] == "low"
    # product: nothing → low
    assert by_axis["product"][0] == "low"


def test_people_axis_medium_with_commits_and_ownership(tmp_path: Path) -> None:
    """With commits_fact + ownership_share, people completeness = 2/3 = 67% → medium."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        _setup_base(conn, "acme", "acme/api")
        conn.execute(
            "INSERT INTO commits_fact (repo_id, commit_sha, author_email, author_date) "
            "VALUES ('acme/api', 'abc123', 'dev@acme.com', '2024-01-01')"
        )
        conn.execute(
            "INSERT INTO ownership_share (repo_id, author_email, owned_loc, owned_files, source) "
            "VALUES ('acme/api', 'dev@acme.com', 1000, 10, 'git-fame')"
        )
        compute_axis_confidence(conn, target_id="acme")
        row = conn.execute(
            "SELECT confidence_class, signal_completeness_pct FROM axis_confidence "
            "WHERE target_id='acme' AND axis='people'"
        ).fetchone()
    assert row[0] == "medium"
    assert abs(row[1] - 66.666) < 1.0


def test_people_axis_high_with_all_sources(tmp_path: Path) -> None:
    """All three people sources populated → high."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        _setup_base(conn, "acme", "acme/api")
        conn.execute(
            "INSERT INTO commits_fact (repo_id, commit_sha, author_email, author_date) "
            "VALUES ('acme/api', 'abc123', 'dev@acme.com', '2024-01-01')"
        )
        conn.execute(
            "INSERT INTO ownership_share (repo_id, author_email, owned_loc, owned_files, source) "
            "VALUES ('acme/api', 'dev@acme.com', 1000, 10, 'git-fame')"
        )
        conn.execute(
            "INSERT INTO contributor_classification (target_id, author_email, class, confidence, signals, source) "
            "VALUES ('acme', 'dev@acme.com', 'fte', 0.9, '{}', 'yaml')"
        )
        compute_axis_confidence(conn, target_id="acme")
        row = conn.execute(
            "SELECT confidence_class FROM axis_confidence WHERE target_id='acme' AND axis='people'"
        ).fetchone()
    assert row[0] == "high"


def test_compute_axis_confidence_is_idempotent(tmp_path: Path) -> None:
    """Calling compute_axis_confidence twice should not duplicate rows."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        _setup_base(conn, "acme", "acme/api")
        compute_axis_confidence(conn, target_id="acme")
        compute_axis_confidence(conn, target_id="acme")
        n = conn.execute(
            "SELECT COUNT(*) FROM axis_confidence WHERE target_id='acme'"
        ).fetchone()[0]
    assert n == 3  # one row per axis
