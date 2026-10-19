import json
from typing import Literal

import duckdb

ConfidenceClass = Literal["high", "medium", "low"]

PLATFORM_COLLECTORS = {
    "pr_metrics": "github-pulls",
    "actions_metrics": "github-actions",
    "release_metrics": "github-releases",
    "issue_metrics": "github-issues",
}


def compute_axis_confidence(
    conn: duckdb.DuckDBPyConnection, *, target_id: str, collected: frozenset[str],
) -> None:
    """Populate axis_confidence; a collected GitHub table without a current failure counts even when empty."""
    conn.execute("DELETE FROM axis_confidence WHERE target_id = ?", [target_id])
    for axis in ("people", "product", "process"):
        completeness, missing = _compute_for_axis(conn, target_id, axis, collected)
        cls = "high" if completeness >= 0.8 else "medium" if completeness >= 0.4 else "low"
        conn.execute(
            "INSERT INTO axis_confidence (target_id, axis, signal_completeness_pct, "
            "missing_sources, confidence_class) VALUES (?, ?, ?, ?, ?)",
            [target_id, axis, completeness * 100, json.dumps(missing), cls],
        )


def _compute_for_axis(conn, target_id, axis, collected):

    expected = {
        "people": ["commits_fact", "ownership_share", "contributor_classification"],
        "product": ["file_metrics", "coupling_pairs", "code_age_buckets", "burndown_series"],
        "process": ["pr_metrics", "actions_metrics", "release_metrics", "issue_metrics"],
    }[axis]
    found, missing = [], []
    for table in expected:
        if table == "contributor_classification":
            n = conn.execute(
                "SELECT COUNT(*) FROM contributor_classification WHERE target_id = ?",
                [target_id],
            ).fetchone()[0]
        else:
            n = conn.execute(
                f"SELECT COUNT(*) FROM {table} JOIN repos ON {table}.repo_id = repos.repo_id WHERE repos.target_id = ?",
                [target_id],
            ).fetchone()[0]
        present = n > 0 or (table in collected and not _collector_failed(conn, target_id, table))
        (found if present else missing).append(table)
    return len(found) / len(expected), missing


def _collector_failed(conn: duckdb.DuckDBPyConnection, target_id: str, table: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) > 0 FROM tool_failures WHERE target_id = ? AND tool = ?",
        [target_id, PLATFORM_COLLECTORS[table]],
    ).fetchone()
    assert row is not None
    return bool(row[0])
