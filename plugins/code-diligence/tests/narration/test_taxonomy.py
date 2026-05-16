from pathlib import Path
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.narration.taxonomy import TAXONOMY, load_taxonomy_into_warehouse


def test_taxonomy_has_all_spec_sections() -> None:
    sections = {(t.axis, t.section_key) for t in TAXONOMY}
    # Spec §6: 5 People + 6 Product + 5 Process = 16 cards in v1
    assert len(sections) == 16
    by_axis = {axis: sum(1 for a, _ in sections if a == axis) for axis in {"people", "product", "process"}}
    assert by_axis == {"people": 5, "product": 6, "process": 5}


def test_load_taxonomy_into_warehouse(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        load_taxonomy_into_warehouse(conn)
        rows = conn.execute("SELECT axis, section_key, title FROM axes_taxonomy ORDER BY axis, section_key").fetchall()
    assert len(rows) == 16
    # Spot-check
    keys = {(r[0], r[1]) for r in rows}
    assert ("people", "bus_factor_map") in keys
    assert ("product", "hotspot_map") in keys
    assert ("process", "dora_quadrant") in keys
