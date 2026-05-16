from pathlib import Path
from unittest.mock import patch

from code_diligence.narration.runner import run_narrator_for_target


@patch("code_diligence.narration.runner._invoke_narrator_agent")
def test_runs_narrator_for_each_section(mock_invoke, tmp_path: Path) -> None:
    mock_invoke.return_value = None  # simulates agent writing via MCP

    # Build a minimal warehouse so quick-tier path runs
    from code_diligence.warehouse.connection import open_warehouse
    from code_diligence.warehouse.migrations import migrate
    from code_diligence.warehouse.targets import register_target
    from code_diligence.narration.taxonomy import load_taxonomy_into_warehouse

    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        load_taxonomy_into_warehouse(conn)
        register_target(conn, target_id="acme", name="Acme")

    run_narrator_for_target(warehouse_path=db, target_id="acme", tier="quick")
    assert mock_invoke.call_count == 16


@patch("code_diligence.narration.runner._invoke_narrator_agent")
def test_quick_tier_marks_process_low_confidence(mock_invoke, tmp_path: Path) -> None:
    """In quick tier, Process axis sections still get a narrator pass but tier='quick' tells the agent to hedge."""
    from code_diligence.warehouse.connection import open_warehouse
    from code_diligence.warehouse.migrations import migrate
    from code_diligence.warehouse.targets import register_target
    from code_diligence.narration.taxonomy import load_taxonomy_into_warehouse

    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        load_taxonomy_into_warehouse(conn)
        register_target(conn, target_id="acme", name="Acme")

    run_narrator_for_target(warehouse_path=db, target_id="acme", tier="quick")
    process_calls = [c for c in mock_invoke.call_args_list if c.kwargs.get("axis") == "process"]
    assert len(process_calls) == 5
    assert all(c.kwargs.get("tier") == "quick" for c in process_calls)
