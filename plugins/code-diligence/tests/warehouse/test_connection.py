from pathlib import Path
from code_diligence.warehouse.connection import open_warehouse


def test_open_warehouse_creates_file(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        result = conn.execute("SELECT 1 AS x").fetchone()
        assert result == (1,)
    assert db_path.exists()


def test_open_warehouse_reopens_existing(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (42)")
    with open_warehouse(db_path) as conn:
        assert conn.execute("SELECT x FROM t").fetchone() == (42,)
