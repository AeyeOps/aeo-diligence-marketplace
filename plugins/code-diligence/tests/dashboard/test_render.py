import shutil
from pathlib import Path

import pytest

from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target


@pytest.mark.skipif(not shutil.which("npm"), reason="npm not installed")
def test_render_produces_static_site(tmp_path: Path) -> None:
    from code_diligence.dashboard.render import render_dashboard

    warehouse = tmp_path / "acme.duckdb"
    with open_warehouse(warehouse) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")

    out = tmp_path / "dashboard"
    render_dashboard(warehouse_path=warehouse, output_path=out)

    assert (out / "index.html").exists()
    html = (out / "index.html").read_text()
    assert "code-diligence" in html.lower()
