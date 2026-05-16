"""GitHub platform pass: per-repo orchestration of platform data fetchers."""
import duckdb

from code_diligence.ingest.isolation import isolated
from code_diligence.github.pulls import fetch_and_persist_prs
from code_diligence.github.actions import fetch_and_persist_actions
from code_diligence.github.releases import fetch_and_persist_releases
from code_diligence.github.issues import fetch_and_persist_issues


def run_platform_pass_for_repo(
    conn: duckdb.DuckDBPyConnection,
    *, target_id: str, repo_id: str, repo_full_name: str, token: str,
    pr_data: bool, actions_data: bool, issues_data: bool,
) -> None:
    """Fetch GitHub-platform data per repo per enabled flag, isolated."""
    if pr_data:
        isolated(conn, target_id=target_id, repo_id=repo_id, tool="github-pulls", tool_version=None,
                 fn=lambda: fetch_and_persist_prs(conn, repo_id=repo_id, repo_full_name=repo_full_name, token=token))
    if actions_data:
        isolated(conn, target_id=target_id, repo_id=repo_id, tool="github-actions", tool_version=None,
                 fn=lambda: fetch_and_persist_actions(conn, repo_id=repo_id, repo_full_name=repo_full_name, token=token))
    if pr_data or actions_data:  # releases are cheap; fetch alongside actions
        isolated(conn, target_id=target_id, repo_id=repo_id, tool="github-releases", tool_version=None,
                 fn=lambda: fetch_and_persist_releases(conn, repo_id=repo_id, repo_full_name=repo_full_name, token=token))
    if issues_data:
        isolated(conn, target_id=target_id, repo_id=repo_id, tool="github-issues", tool_version=None,
                 fn=lambda: fetch_and_persist_issues(conn, repo_id=repo_id, repo_full_name=repo_full_name, token=token))
