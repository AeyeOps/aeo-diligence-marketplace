from pathlib import Path
import duckdb

from code_diligence.ingest.isolation import isolated
from code_diligence.tools.code_maat import (
    build_log_dump, run_code_maat_analysis, persist_revisions, persist_coupling, persist_entity_ownership,
)
from code_diligence.tools.hercules import run_hercules_burndown, persist_burndown
from code_diligence.tools.repowise import fetch_repowise_findings_for_repo, persist_repowise


def run_expensive_tools_for_repo(
    conn: duckdb.DuckDBPyConnection,
    *, target_id: str, repo_id: str, repo_path: Path,
) -> None:
    """Run code-maat (multiple analyses), hercules, repowise; each isolated."""
    import tempfile

    def _code_maat():
        with tempfile.TemporaryDirectory() as td:
            log = build_log_dump(repo_path, out=Path(td) / "log.txt")
            persist_revisions(conn, repo_id=repo_id, csv_text=run_code_maat_analysis(log, analysis="revisions"))
            persist_coupling(conn, repo_id=repo_id, csv_text=run_code_maat_analysis(log, analysis="coupling"))
            persist_entity_ownership(conn, repo_id=repo_id, csv_text=run_code_maat_analysis(log, analysis="entity-ownership"))

    def _hercules():
        persist_burndown(conn, repo_id=repo_id, payload=run_hercules_burndown(repo_path))

    def _repowise():
        persist_repowise(conn, repo_id=repo_id, findings=fetch_repowise_findings_for_repo(repo_path))

    for tool, fn in [("code-maat", _code_maat), ("hercules", _hercules), ("repowise", _repowise)]:
        isolated(conn, target_id=target_id, repo_id=repo_id, tool=tool, tool_version=None, fn=fn)
