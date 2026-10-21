"""Prepare monthly commit and code-line activity from the collected history."""

import json
from datetime import date
from pathlib import Path

import duckdb
from git_of_theseus.analyze import default_filetypes
from wcmatch import fnmatch


def write_activity_data(
    conn: duckdb.DuckDBPyConnection, path: Path, targets: list[str],
) -> None:
    """Use the same source-file selection as git-of-theseus for line changes."""
    data: dict[str, dict[str, dict[str, int]]] = {target: {} for target in targets}
    for target, month, commits in conn.execute("""
        SELECT r.target_id, strftime(cf.author_date, '%Y-%m-01'), COUNT(*)
        FROM commits_fact cf JOIN repos r ON r.repo_id = cf.repo_id
        GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall():
        data[target][month] = {"commits": commits, "added": 0, "removed": 0}
    matcher = fnmatch.compile(
        "+(" + "|".join(sorted(default_filetypes)) + ")", flags=fnmatch.EXTMATCH,
    )
    cursor = conn.execute("""
        SELECT r.target_id, strftime(cf.author_date, '%Y-%m-01'),
               regexp_extract(cf.file_path, '[^/]+$'),
               SUM(cf.lines_added), SUM(cf.lines_removed)
        FROM commit_file_authors cf JOIN repos r ON r.repo_id = cf.repo_id
        GROUP BY 1, 2, 3
    """)
    while batch := cursor.fetchmany(512):
        for target, month, filename, added, removed in batch:
            if matcher.match(filename):
                row = data[target][month]
                row["added"] += added
                row["removed"] += removed
    output = {}
    for target, months in data.items():
        rows = []
        if months:
            month = date.fromisoformat(min(months))
            last = date.fromisoformat(max(months))
            while month <= last:
                key = month.isoformat()
                rows.append({"month": key, **months.get(key, {"commits": 0, "added": 0, "removed": 0})})
                month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
        output[target] = rows
    path.write_text(json.dumps(output))
