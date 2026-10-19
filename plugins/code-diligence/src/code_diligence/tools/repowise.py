"""Collect Repowise health and dead-code findings through its CLI."""
import json
import os
import subprocess
from pathlib import Path

import duckdb


def fetch_repowise_for_repo(repo: Path) -> tuple[dict, list[dict]]:
    """Recompute health without writes; return its summary scores and the health and dead-code findings."""
    kpis: dict = {}
    findings = []
    for command, extra in (("health", ["--recompute"]), ("dead-code", [])):
        proc = subprocess.run(
            ["repowise", command, str(repo), "--format", "json", "--no-workspace", *extra],
            capture_output=True, text=True, timeout=300, check=True,
            env=os.environ | {"REPOWISE_TELEMETRY_DISABLED": "1"},
        )
        payload = json.loads(proc.stdout)
        if command == "health":
            kpis = payload["kpis"]
        rows = payload["findings"] if command == "health" else payload
        for row in rows:
            symbol = row["function_name"] if command == "health" else row["symbol_name"]
            scope = f"{row['file_path']}:{symbol}" if symbol else row["file_path"]
            findings.append({
                **row, "scope": scope,
                "type": row["biomarker_type"] if command == "health" else row["kind"],
            })
    return kpis, findings


def persist_repowise(conn: duckdb.DuckDBPyConnection, *, repo_id: str, kpis: dict, findings: list[dict]) -> None:
    conn.execute("DELETE FROM repowise_health WHERE repo_id = ?", [repo_id])
    conn.execute(
        "INSERT INTO repowise_health (repo_id, average_health, hotspot_health, maintainability_average, "
        "performance_average, file_count, worst_path, worst_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [repo_id, kpis["average_health"], kpis["hotspot_health"], kpis["maintainability_average"],
         kpis["performance_average"], kpis["file_count"], kpis["worst_performer_path"], kpis["worst_performer_score"]],
    )
    conn.execute("DELETE FROM repowise_findings WHERE repo_id = ?", [repo_id])
    rows = [
        (repo_id, f.get("scope", ""), f.get("type", ""), f.get("severity", ""), json.dumps(f))
        for f in findings
    ]
    if not rows:
        return
    conn.executemany(
        "INSERT INTO repowise_findings (repo_id, scope, finding_type, severity, evidence) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
