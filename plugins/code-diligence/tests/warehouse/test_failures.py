from pathlib import Path

from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.failures import list_failures, log_failure
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target


def test_log_failure_records_row(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        log_failure(
            conn,
            target_id="acme",
            repo_id="acme/api",
            tool="code-maat",
            tool_version="1.0.4",
            failure_class="crash",
            message="JVM OOM",
        )
        rows = list_failures(conn, target_id="acme")
    assert len(rows) == 1
    assert rows[0]["tool"] == "code-maat"
    assert rows[0]["class"] == "crash"


def test_list_failures_filters_by_tool(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        log_failure(conn, target_id="acme", tool="code-maat", failure_class="crash")
        log_failure(conn, target_id="acme", tool="hercules", failure_class="timeout")
        only_maat = list_failures(conn, target_id="acme", tool="code-maat")
    assert len(only_maat) == 1
    assert only_maat[0]["tool"] == "code-maat"
