import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import yaml


HERCULES_VERSION = "10.7.2"  # pinned


class HerculesError(RuntimeError): ...


def run_hercules_burndown(repo: Path) -> dict[str, Any]:
    """Run hercules burndown analysis; return parsed YAML."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        out_path = Path(f.name)
    try:
        proc = subprocess.run(
            ["hercules", "--burndown", "--burndown-people", "--yaml", str(repo)],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            raise HerculesError(f"hercules failed: {proc.stderr.strip()}")
        return yaml.safe_load(proc.stdout)
    finally:
        out_path.unlink(missing_ok=True)


def persist_burndown(conn: duckdb.DuckDBPyConnection, *, repo_id: str, payload: dict) -> None:
    """Extract per-tick per-vintage surviving LOC into burndown_series."""
    burndown = payload.get("Burndown", {})
    project = burndown.get("project", {})
    matrix = project.get("matrix", [])
    granularity = project.get("granularity", 30)  # days per tick
    sampling = project.get("sampling", 30)
    start = datetime.fromisoformat(payload.get("hercules", {}).get("begin_unix_time", "1970-01-01"))
    conn.execute("DELETE FROM burndown_series WHERE repo_id = ?", [repo_id])
    rows = []
    for tick_idx, tick in enumerate(matrix):
        snapshot_at = start  # implementer: compute from tick_idx * sampling days
        for vintage_idx, loc in enumerate(tick):
            if loc == 0:
                continue
            vintage_year = (start.year - tick_idx + vintage_idx)  # heuristic — refine in real impl
            rows.append((repo_id, snapshot_at, vintage_year, int(loc)))
    conn.executemany(
        "INSERT INTO burndown_series (repo_id, snapshot_at, vintage_year, surviving_loc) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )
