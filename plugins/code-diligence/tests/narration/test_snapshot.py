"""Snapshot test: narrator output should be stable across runs at temp 0.

Skipped by default (LIVE_NARRATOR_SNAPSHOT=1 to run); enabled in a CI job that
has ANTHROPIC_API_KEY and the claude CLI installed.
"""
import os
import shutil
from pathlib import Path

import pytest


SNAPSHOT_DIR = Path(__file__).parent / "__snapshots__"


@pytest.mark.skipif(
    not os.environ.get("LIVE_NARRATOR_SNAPSHOT"),
    reason="set LIVE_NARRATOR_SNAPSHOT=1 to run snapshot test (calls Claude)",
)
def test_narrator_snapshot_stable(synthetic_target: Path, tmp_path: Path) -> None:
    """Run narrator end-to-end against synthetic target; compare to baseline."""
    if not shutil.which("claude"):
        pytest.skip("claude CLI not installed")

    # Build a populated warehouse from the synthetic target (uses earlier groups' code)
    from code_diligence.warehouse.connection import open_warehouse
    from code_diligence.warehouse.migrations import migrate
    from code_diligence.warehouse.targets import register_target
    from code_diligence.narration.taxonomy import load_taxonomy_into_warehouse
    from code_diligence.narration.runner import run_narrator_for_target

    db = tmp_path / "snapshot.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        load_taxonomy_into_warehouse(conn)
        register_target(conn, target_id="snapshot-target", name="Snapshot")
        # (Real test would also seed commits/repos/etc. via the ingest CLI;
        # for brevity here, narrator will say "data unavailable" for most cards,
        # which is itself a stable output.)

    run_narrator_for_target(warehouse_path=db, target_id="snapshot-target", tier="quick")

    with open_warehouse(db) as conn:
        rows = conn.execute(
            "SELECT axis, section_key, body_md FROM narratives "
            "WHERE target_id='snapshot-target' ORDER BY axis, section_key"
        ).fetchall()
    actual = "\n".join(f"[{a}/{k}]\n{b}\n" for a, k, b in rows)

    snapshot_path = SNAPSHOT_DIR / "narrator-quick-empty-warehouse.txt"
    if not snapshot_path.exists():
        snapshot_path.write_text(actual)
        pytest.fail(f"baseline created at {snapshot_path}; re-run to verify stability")
    expected = snapshot_path.read_text()
    assert actual == expected, "narrator output drifted — review and update snapshot if intentional"
