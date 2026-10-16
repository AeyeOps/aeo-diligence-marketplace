"""Collect Repowise health and dead-code findings through its CLI."""
import json
import subprocess
from pathlib import Path

import duckdb


def fetch_repowise_findings_for_repo(repo: Path) -> list[dict]:
    """Recompute health without writes and read the repository's dead-code findings."""
    findings = []
    for command, extra in (("health", ["--recompute"]), ("dead-code", [])):
        proc = subprocess.run(
            ["repowise", command, str(repo), "--format", "json", "--no-workspace", *extra],
            capture_output=True, text=True, timeout=300, check=True,
        )
        payload = json.loads(proc.stdout)
        rows = payload["findings"] if command == "health" else payload
        for row in rows:
            symbol = row["function_name"] if command == "health" else row["symbol_name"]
            scope = f"{row['file_path']}:{symbol}" if symbol else row["file_path"]
            findings.append({
                **row, "scope": scope,
                "type": row["biomarker_type"] if command == "health" else row["kind"],
            })
    return findings


def persist_repowise(conn: duckdb.DuckDBPyConnection, *, repo_id: str, findings: list[dict]) -> None:
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
