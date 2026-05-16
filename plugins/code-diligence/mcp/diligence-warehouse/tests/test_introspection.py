"""Tests for list_tables and describe_table — call the underlying handlers directly."""
from pathlib import Path
import pytest

import duckdb

# Import the handler functions, not the MCP wiring (we test logic, not transport)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from server import handle_list_tables, handle_describe_table  # noqa: E402


def _build_test_warehouse(path: Path) -> None:
    conn = duckdb.connect(str(path))
    conn.execute("CREATE TABLE foo (id INTEGER, name VARCHAR)")
    conn.execute("CREATE TABLE bar (x DOUBLE, y TIMESTAMP, payload JSON)")
    conn.close()


def test_list_tables_returns_user_tables(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    _build_test_warehouse(db)
    result = handle_list_tables(db)
    table_names = {t["name"] for t in result["tables"]}
    assert "foo" in table_names
    assert "bar" in table_names


def test_describe_table_returns_columns(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    _build_test_warehouse(db)
    result = handle_describe_table(db, "foo")
    cols = {c["name"]: c["type"] for c in result["columns"]}
    assert cols == {"id": "INTEGER", "name": "VARCHAR"}


def test_describe_table_unknown_table_raises(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    _build_test_warehouse(db)
    with pytest.raises(ValueError, match="unknown table"):
        handle_describe_table(db, "nonexistent")
