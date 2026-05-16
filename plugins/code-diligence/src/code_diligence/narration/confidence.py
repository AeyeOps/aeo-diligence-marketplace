import json
from typing import Literal

import duckdb

ConfidenceClass = Literal["high", "medium", "low"]


def compute_axis_confidence(conn: duckdb.DuckDBPyConnection, *, target_id: str) -> None:
    """Populate axis_confidence rows for People / Product / Process."""
    conn.execute("DELETE FROM axis_confidence WHERE target_id = ?", [target_id])
    for axis in ("people", "product", "process"):
        completeness, missing = _compute_for_axis(conn, target_id, axis)
        cls = "high" if completeness >= 0.8 else "medium" if completeness >= 0.4 else "low"
        conn.execute(
            "INSERT INTO axis_confidence (target_id, axis, signal_completeness_pct, "
            "missing_sources, confidence_class) VALUES (?, ?, ?, ?, ?)",
            [target_id, axis, completeness * 100, json.dumps(missing), cls],
        )


def _compute_for_axis(conn, target_id, axis):
    # Each axis has a list of "expected populated tables"; missing ones penalize completeness
    expected = {
        "people": ["commits_fact", "ownership_share", "contributor_classification"],
        "product": ["file_metrics", "coupling_pairs", "code_age_buckets", "burndown_series"],
        "process": ["pr_metrics", "actions_metrics", "release_metrics", "issue_metrics"],
    }[axis]
    found, missing = [], []
    for table in expected:
        if table == "contributor_classification":
            n = conn.execute(
                f"SELECT COUNT(*) FROM contributor_classification WHERE target_id = ?",
                [target_id],
            ).fetchone()[0]
        else:
            n = conn.execute(
                f"SELECT COUNT(*) FROM {table} JOIN repos ON {table}.repo_id = repos.repo_id WHERE repos.target_id = ?",
                [target_id],
            ).fetchone()[0]
        (found if n > 0 else missing).append(table)
    return len(found) / len(expected), missing
