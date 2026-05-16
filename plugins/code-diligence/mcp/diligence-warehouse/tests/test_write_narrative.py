import sys
from pathlib import Path
import pytest
import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))
from server import handle_write_narrative, WriteNarrativeError  # noqa: E402


@pytest.fixture
def warehouse_with_target(tmp_path: Path) -> Path:
    db = tmp_path / "t.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute("""
        CREATE TABLE narratives (
          target_id VARCHAR, axis VARCHAR, section_key VARCHAR,
          body_md VARCHAR, generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          generator_version VARCHAR, tier VARCHAR,
          PRIMARY KEY (target_id, axis, section_key)
        )
    """)
    conn.close()
    return db


def test_write_narrative_inserts(warehouse_with_target: Path) -> None:
    handle_write_narrative(
        warehouse_with_target, target_id="acme", axis="people",
        section_key="bus_factor_map", body_md="Pat owns 90% of api.", tier="quick",
    )
    conn = duckdb.connect(str(warehouse_with_target), read_only=True)
    rows = conn.execute("SELECT body_md, tier FROM narratives").fetchall()
    conn.close()
    assert rows == [("Pat owns 90% of api.", "quick")]


def test_write_narrative_upserts(warehouse_with_target: Path) -> None:
    for body in ["v1", "v2", "v3"]:
        handle_write_narrative(
            warehouse_with_target, target_id="acme", axis="people",
            section_key="bus_factor_map", body_md=body, tier="quick",
        )
    conn = duckdb.connect(str(warehouse_with_target), read_only=True)
    rows = conn.execute("SELECT body_md FROM narratives").fetchall()
    conn.close()
    assert rows == [("v3",)]  # final write wins, single row


@pytest.mark.parametrize("axis,tier,err", [
    ("badaxis", "quick", "axis"),
    ("people", "badtier", "tier"),
    ("", "quick", "axis"),
])
def test_write_narrative_validates(warehouse_with_target: Path, axis: str, tier: str, err: str) -> None:
    with pytest.raises(WriteNarrativeError, match=err):
        handle_write_narrative(
            warehouse_with_target, target_id="acme", axis=axis,
            section_key="x", body_md="y", tier=tier,
        )
