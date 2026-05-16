"""75c: privacy gate — render_dashboard writes config.json reflecting the flag.

Mocks the npm/observable subprocess + filesystem-copy steps so we exercise
only the config.json write contract that drives the dashboard's gate on
heuristics.allow_working_pattern_card.
"""
import json
from pathlib import Path

import pytest

from code_diligence.dashboard import render
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target


CONFIG_PATH = render.TEMPLATE_DIR / "src" / "data" / "config.json"


@pytest.fixture
def patched_render(monkeypatch, tmp_path: Path):
    """Yield a render_dashboard caller with subprocess + dist-copy stubbed out."""
    monkeypatch.setattr(render.subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(render.shutil, "copy", lambda *a, **kw: None)
    monkeypatch.setattr(render.shutil, "copytree", lambda *a, **kw: None)
    monkeypatch.setattr(render.shutil, "rmtree", lambda *a, **kw: None)
    # Make the node_modules check pass without running npm install
    monkeypatch.setattr(render.Path, "exists", lambda self: True)
    warehouse = tmp_path / "wh.duckdb"
    with open_warehouse(warehouse) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
    output = tmp_path / "out"
    return warehouse, output


def test_render_writes_config_with_flag_off_by_default(patched_render) -> None:
    warehouse, output = patched_render
    render.render_dashboard(warehouse_path=warehouse, output_path=output)
    cfg = json.loads(CONFIG_PATH.read_text())
    assert cfg == {"allow_working_pattern_card": False}


def test_render_writes_config_with_flag_on_when_passed(patched_render) -> None:
    warehouse, output = patched_render
    render.render_dashboard(
        warehouse_path=warehouse, output_path=output,
        allow_working_pattern_card=True,
    )
    cfg = json.loads(CONFIG_PATH.read_text())
    assert cfg == {"allow_working_pattern_card": True}
