import shutil
from pathlib import Path

import pytest

from code_diligence.tools.git_of_theseus import (
    CodeAgeBucket,
    parse_cohorts_json,
    persist_git_of_theseus,
    run_git_of_theseus,
)
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


def test_parse_cohorts_json_fixture() -> None:
    """Pure parser test — works without git-of-theseus installed."""
    sample = {
        "y": [
            [100, 50, 25],  # earlier snapshot
            [80, 60, 40],   # latest snapshot
        ],
        "ts": ["2020-01-01T00:00:00", "2024-01-01T00:00:00"],
        "labels": ["2019", "2020-06", "2021"],
    }
    records = parse_cohorts_json(sample)
    assert len(records) == 3
    by_year = {r.bucket_start_year: r.surviving_loc for r in records}
    assert by_year[2019] == 80
    assert by_year[2020] == 60
    assert by_year[2021] == 40


def test_parse_cohorts_json_empty() -> None:
    assert parse_cohorts_json({}) == []
    assert parse_cohorts_json({"y": []}) == []


def test_parse_cohorts_json_skips_non_year_labels() -> None:
    sample = {
        "y": [[10, 20]],
        "labels": ["nope", "2022"],
    }
    records = parse_cohorts_json(sample)
    assert len(records) == 1
    assert records[0].bucket_start_year == 2022


@pytest.mark.skipif(not shutil.which("git-of-theseus-analyze"), reason="git-of-theseus not installed")
def test_run_git_of_theseus_returns_records(synthetic_target: Path) -> None:
    records = run_git_of_theseus(synthetic_target / "api")
    assert all(isinstance(r, CodeAgeBucket) for r in records)


@pytest.mark.skipif(not shutil.which("git-of-theseus-analyze"), reason="git-of-theseus not installed")
def test_persist_writes_code_age_buckets(synthetic_target: Path, tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url=str(synthetic_target / "api"))
        records = run_git_of_theseus(synthetic_target / "api")
        persist_git_of_theseus(conn, repo_id="acme/api", buckets=records)
        rows = conn.execute(
            "SELECT bucket_start_year, surviving_loc FROM code_age_buckets "
            "WHERE repo_id='acme/api'"
        ).fetchall()
    assert len(rows) == len(records)


def test_persist_replaces_existing_rows(tmp_path: Path) -> None:
    """Pure DB test — exercises persist without needing the binary."""
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme",
                    name="api", source_url="local")
        persist_git_of_theseus(conn, repo_id="acme/api", buckets=[
            CodeAgeBucket(bucket_start_year=2020, surviving_loc=100),
            CodeAgeBucket(bucket_start_year=2021, surviving_loc=200),
        ])
        # Second call replaces
        persist_git_of_theseus(conn, repo_id="acme/api", buckets=[
            CodeAgeBucket(bucket_start_year=2022, surviving_loc=50),
        ])
        rows = conn.execute(
            "SELECT bucket_start_year, surviving_loc FROM code_age_buckets "
            "WHERE repo_id='acme/api' ORDER BY bucket_start_year"
        ).fetchall()
    assert rows == [(2022, 50)]
