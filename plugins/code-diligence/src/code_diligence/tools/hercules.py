"""Read Hercules' YAML burndown matrix using its declared time units."""
import subprocess
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import yaml

HERCULES_VERSION = "10.7.2"


class HerculesError(RuntimeError):
    """Hercules did not complete the requested analysis."""


def run_hercules_burndown(repo: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["hercules", "--burndown", "--burndown-people", str(repo)],
        capture_output=True, text=True, timeout=600, check=True,
    )
    return yaml.safe_load(proc.stdout)


def persist_burndown(conn: duckdb.DuckDBPyConnection, *, repo_id: str, payload: dict) -> None:
    burndown = payload["Burndown"]
    tick_size = int(burndown["tick_size"])
    begin = int(payload["hercules"]["begin_unix_time"])
    end = datetime.fromtimestamp(int(payload["hercules"]["end_unix_time"]), UTC)
    start = datetime.fromtimestamp(begin - begin % tick_size, UTC)
    sampling = int(burndown["sampling"])
    granularity = int(burndown["granularity"])
    matrix = [[int(value) for value in line.split()] for line in burndown["project"].splitlines() if line.strip()]
    totals: dict[tuple[datetime, int], int] = defaultdict(int)
    for sample_index, vintages in enumerate(matrix):
        snapshot = min(start + timedelta(seconds=(sample_index + 1) * sampling * tick_size), end)
        for vintage_index, loc in enumerate(vintages):
            vintage = (start + timedelta(seconds=vintage_index * granularity * tick_size)).year
            totals[snapshot, vintage] += loc
    conn.execute("DELETE FROM burndown_series WHERE repo_id = ?", [repo_id])
    rows = [(repo_id, snapshot, vintage, loc) for (snapshot, vintage), loc in sorted(totals.items()) if loc]
    if rows:
        conn.executemany(
            "INSERT INTO burndown_series (repo_id, snapshot_at, vintage_year, surviving_loc) VALUES (?, ?, ?, ?)",
            rows,
        )
