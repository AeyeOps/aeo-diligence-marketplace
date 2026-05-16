from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb


@contextmanager
def open_warehouse(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open (or create) a DuckDB warehouse file. Closes connection on exit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    try:
        yield conn
    finally:
        conn.close()
