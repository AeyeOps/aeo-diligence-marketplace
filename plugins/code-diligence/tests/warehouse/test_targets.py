from pathlib import Path

from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import get_target, register_target


def test_register_target_inserts_row(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme Corp", description="test")
        row = get_target(conn, "acme")
    assert row is not None
    assert row["target_id"] == "acme"
    assert row["name"] == "Acme Corp"
    assert row["ingested_at"] is not None


def test_register_target_updates_existing(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme Corp", description="v1")
        register_target(conn, target_id="acme", name="Acme Corp", description="v2")
        row = get_target(conn, "acme")
        count = conn.execute("SELECT COUNT(*) FROM targets WHERE target_id='acme'").fetchone()[0]
    assert row is not None
    assert row["description"] == "v2"
    assert count == 1


def test_get_target_returns_none_when_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        assert get_target(conn, "nonexistent") is None
