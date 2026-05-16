"""Adapter that consumes the external repowise MCP and persists findings."""
import json
import subprocess
from pathlib import Path

import duckdb


def fetch_repowise_findings_for_repo(repo: Path) -> list[dict]:
    """Invoke repowise CLI in JSON mode (CLI alternative to its MCP for batch use)."""
    try:
        proc = subprocess.run(
            ["repowise", "analyze", "--json", str(repo)],
            capture_output=True, text=True, timeout=300,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    return json.loads(proc.stdout).get("findings", [])


def persist_repowise(conn: duckdb.DuckDBPyConnection, *, repo_id: str, findings: list[dict]) -> None:
    conn.execute("DELETE FROM repowise_findings WHERE repo_id = ?", [repo_id])
    rows = [
        (repo_id, f.get("scope", ""), f.get("type", ""), f.get("severity", ""), json.dumps(f))
        for f in findings
    ]
    conn.executemany(
        "INSERT INTO repowise_findings (repo_id, scope, finding_type, severity, evidence) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
