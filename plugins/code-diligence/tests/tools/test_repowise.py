import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.tools.repowise import fetch_repowise_findings_for_repo, persist_repowise


def test_fetch_repowise_returns_empty_when_binary_missing(tmp_path: Path) -> None:
    """Returns [] when repowise binary is not available."""
    with patch("code_diligence.tools.repowise.subprocess.run", side_effect=FileNotFoundError):
        result = fetch_repowise_findings_for_repo(tmp_path)
    assert result == []


def test_fetch_repowise_returns_empty_on_nonzero_exit(tmp_path: Path) -> None:
    """Returns [] when repowise exits nonzero."""
    import subprocess
    mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
    with patch("code_diligence.tools.repowise.subprocess.run", return_value=mock_result):
        result = fetch_repowise_findings_for_repo(tmp_path)
    assert result == []


def test_persist_repowise_writes_rows(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    findings = [
        {"scope": "api/main.py", "type": "complexity", "severity": "high", "detail": "cyclomatic=15"},
        {"scope": "api/auth.py", "type": "duplication", "severity": "medium"},
    ]
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url=str(tmp_path))
        persist_repowise(conn, repo_id="acme/api", findings=findings)
        rows = conn.execute(
            "SELECT scope, finding_type, severity FROM repowise_findings WHERE repo_id='acme/api'"
        ).fetchall()
    assert len(rows) == 2
    scopes = {r[0] for r in rows}
    assert "api/main.py" in scopes
    assert "api/auth.py" in scopes
