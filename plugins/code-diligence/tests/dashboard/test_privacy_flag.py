"""Build the dashboard with each privacy setting and inspect its shipped config."""
import json
import shutil
from pathlib import Path

import pytest

from code_diligence.dashboard.render import TEMPLATE_DIR, render_dashboard
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target


@pytest.mark.skipif(not shutil.which("npm"), reason="npm not installed")
@pytest.mark.parametrize("enabled", [False, True])
def test_render_ships_privacy_setting(tmp_path: Path, enabled: bool) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    with open_warehouse(warehouse) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
    template = (TEMPLATE_DIR / "src" / "data" / "warehouse.js").read_bytes()
    output = tmp_path / "dashboard"
    render_dashboard(
        warehouse_path=warehouse,
        output_path=output,
        allow_working_pattern_card=enabled,
    )
    configs = list((output / "_file" / "data").glob("config.*.json"))
    assert len(configs) == 1
    assert json.loads(configs[0].read_text()) == {
        "allow_working_pattern_card": enabled, "targets": ["acme"],
    }
    assert (output / "targets" / "acme" / "process.html").exists()
    assert (TEMPLATE_DIR / "src" / "data" / "warehouse.js").read_bytes() == template
