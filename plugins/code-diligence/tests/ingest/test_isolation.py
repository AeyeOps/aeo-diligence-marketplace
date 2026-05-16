from pathlib import Path

from code_diligence.ingest.isolation import isolated
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.failures import list_failures
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target


def _raise_boom() -> None:
    raise RuntimeError("boom")


def test_isolated_logs_and_returns_none_on_exception(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        result = isolated(
            conn, target_id="acme", repo_id="acme/bad", tool="walker",
            tool_version="0.1.0", fn=_raise_boom,
        )
        failures = list_failures(conn, target_id="acme")
    assert result is None
    assert len(failures) == 1
    assert failures[0]["class"] == "crash"
    assert "boom" in failures[0]["message"]


def test_isolated_passes_through_on_success(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        result = isolated(
            conn, target_id="acme", repo_id="acme/ok", tool="walker",
            tool_version="0.1.0", fn=lambda: 42,
        )
    assert result == 42
