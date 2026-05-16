import sys
from pathlib import Path
import pytest
import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))
from server import handle_read_query, ReadQueryError  # noqa: E402


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    db = tmp_path / "t.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute("CREATE TABLE t (x INTEGER, y VARCHAR)")
    conn.executemany("INSERT INTO t VALUES (?, ?)", [(1, "a"), (2, "b"), (3, "c")])
    conn.close()
    return db


def test_select_returns_rows(warehouse: Path) -> None:
    result = handle_read_query(warehouse, "SELECT x, y FROM t ORDER BY x")
    assert result["columns"] == ["x", "y"]
    assert result["rows"] == [[1, "a"], [2, "b"], [3, "c"]]
    assert result["row_count"] == 3


def test_with_cte_then_select_allowed(warehouse: Path) -> None:
    result = handle_read_query(
        warehouse, "WITH a AS (SELECT * FROM t) SELECT COUNT(*) AS n FROM a"
    )
    assert result["rows"] == [[3]]


@pytest.mark.parametrize("sql", [
    "INSERT INTO t VALUES (4, 'd')",
    "UPDATE t SET y = 'z'",
    "DELETE FROM t",
    "DROP TABLE t",
    "CREATE TABLE bad (x INTEGER)",
    "ALTER TABLE t ADD COLUMN z INTEGER",
    "TRUNCATE t",
    "ATTACH '/tmp/x.duckdb' AS other",
])
def test_non_select_rejected(warehouse: Path, sql: str) -> None:
    with pytest.raises(ReadQueryError, match="not allowed"):
        handle_read_query(warehouse, sql)


def test_multiple_statements_rejected(warehouse: Path) -> None:
    with pytest.raises(ReadQueryError, match="single statement"):
        handle_read_query(warehouse, "SELECT 1; SELECT 2")


def test_invalid_sql_rejected(warehouse: Path) -> None:
    with pytest.raises(ReadQueryError):
        handle_read_query(warehouse, "SELECT FROM WHERE")
