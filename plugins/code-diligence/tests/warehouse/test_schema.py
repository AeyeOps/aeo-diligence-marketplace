from pathlib import Path
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.schema import init_schema, SCHEMA_VERSION


def test_init_schema_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        init_schema(conn)
        tables = {row[0] for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()}
    expected = {
        "targets", "repos", "authors", "axes_taxonomy",
        "identity_map", "contributor_classification", "repo_classification",
        "commits_fact", "commit_file_authors",
        "file_metrics", "coupling_pairs", "bus_factor",
        "code_age_buckets", "burndown_series", "ownership_share",
        "repowise_findings",
        "pr_metrics", "actions_metrics", "release_metrics", "issue_metrics",
        "narratives", "axis_confidence", "tool_failures",
        "schema_version",
    }
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"


def test_commit_file_authors_columns(tmp_path: Path) -> None:
    """75b: commit_file_authors has the per-file author edge columns."""
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        init_schema(conn)
        cols = {row[0] for row in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'commit_file_authors'"
        ).fetchall()}
    expected = {"repo_id", "commit_sha", "author_email", "author_date",
                "file_path", "lines_added", "lines_removed"}
    assert expected.issubset(cols), f"Missing columns: {expected - cols}"


def test_init_schema_records_version(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        init_schema(conn)
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_init_schema_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        init_schema(conn)
        init_schema(conn)
        count = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
    assert count == 1
