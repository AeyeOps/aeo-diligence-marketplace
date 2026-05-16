from pathlib import Path

from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import MIGRATIONS, current_version, migrate
from code_diligence.warehouse.schema import SCHEMA_VERSION


def test_migrate_on_fresh_db_initializes_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        assert current_version(conn) == SCHEMA_VERSION


def test_current_version_returns_zero_when_no_table(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.duckdb"
    with open_warehouse(db_path) as conn:
        assert current_version(conn) == 0


def test_migrate_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        migrate(conn)
        assert current_version(conn) == SCHEMA_VERSION
