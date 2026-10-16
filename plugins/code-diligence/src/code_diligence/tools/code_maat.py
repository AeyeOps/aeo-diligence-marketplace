"""Wrapper for adamtornhill/code-maat (multi-analysis CSV outputs).

Workflow per repo:
  1. build_log_dump() — git log in code-maat's expected format
  2. run_code_maat_analysis(log, analysis=...) — invoke JAR per analysis
  3. parse_*_csv() + persist_*() — into warehouse
"""
import csv
import io
import subprocess
from collections import defaultdict
from pathlib import Path

import duckdb

CODE_MAAT_VERSION = "1.0.4-SNAPSHOT"
CODE_MAAT_JAR = Path(__file__).resolve().parents[3] / "vendor" / f"code-maat-{CODE_MAAT_VERSION}-standalone.jar"


class CodeMaatError(RuntimeError): ...


def build_log_dump(repo: Path, *, out: Path) -> Path:
    """Build the git log dump in code-maat's expected format."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "--numstat", "--date=short", "--no-renames",
         "--pretty=format:--%h--%ad--%aN"],
        capture_output=True, text=True, check=True, timeout=300,
    )
    out.write_text(proc.stdout)
    return out


def run_code_maat_analysis(log_dump: Path, *, analysis: str) -> str:
    """Invoke code-maat with a specific analysis; return CSV stdout."""
    if not CODE_MAAT_JAR.exists():
        raise CodeMaatError(f"code-maat JAR not vendored at {CODE_MAAT_JAR}; see vendor/README.md")
    proc = subprocess.run(
        ["java", "-jar", str(CODE_MAAT_JAR), "-l", str(log_dump), "-c", "git2", "-a", analysis],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise CodeMaatError(f"code-maat analysis={analysis} failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_revisions_csv(text: str) -> list[tuple[str, int]]:
    reader = csv.DictReader(io.StringIO(text))
    return [(row["entity"], int(row["n-revs"])) for row in reader if row.get("entity")]


def persist_revisions(conn: duckdb.DuckDBPyConnection, *, repo_id: str, csv_text: str) -> None:
    rows = parse_revisions_csv(csv_text)

    for path, n_revs in rows:
        conn.execute(
            "UPDATE file_metrics SET revisions = ? WHERE repo_id = ? AND path = ?",
            [n_revs, repo_id, path],
        )


def parse_coupling_csv(text: str) -> list[tuple[str, str, int, float]]:
    """Parse code-maat coupling CSV: entity,coupled,degree,average-revs."""
    reader = csv.DictReader(io.StringIO(text))
    return [
        (row["entity"], row["coupled"], int(row["degree"]), float(row["average-revs"]))
        for row in reader if row.get("entity")
    ]


def persist_coupling(conn: duckdb.DuckDBPyConnection, *, repo_id: str, csv_text: str) -> None:
    rows = parse_coupling_csv(csv_text)
    conn.execute("DELETE FROM coupling_pairs WHERE repo_id = ? AND source = 'code-maat'", [repo_id])
    db_rows = []
    for file_a, file_b, _degree, _average in rows:
        shared, revisions_a, revisions_b, total = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM (
                SELECT commit_sha FROM commit_file_authors WHERE repo_id = ? AND file_path = ?
                INTERSECT SELECT commit_sha FROM commit_file_authors WHERE repo_id = ? AND file_path = ?
              )),
              (SELECT COUNT(*) FROM commit_file_authors WHERE repo_id = ? AND file_path = ?),
              (SELECT COUNT(*) FROM commit_file_authors WHERE repo_id = ? AND file_path = ?),
              (SELECT COUNT(*) FROM commits_fact WHERE repo_id = ?)
            """,
            [repo_id, file_a, repo_id, file_b, repo_id, file_a, repo_id, file_b, repo_id],
        ).fetchall()[0]
        if total and revisions_a and revisions_b:
            db_rows.append((repo_id, file_a, file_b, shared, shared / total,
                            shared * total / (revisions_a * revisions_b), "code-maat"))
    if db_rows:
        conn.executemany(
            "INSERT INTO coupling_pairs (repo_id, file_a, file_b, co_change_count, support_pct, lift, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", db_rows,
        )


def parse_entity_ownership_csv(text: str) -> list[tuple[str, str, int, float]]:
    """Calculate each author's share of additions from entity-ownership rows."""
    rows = list(csv.DictReader(io.StringIO(text)))
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        totals[row["entity"]] += int(row["added"])
    return [
        (row["entity"], row["author"], int(row["added"]),
         int(row["added"]) / totals[row["entity"]] if totals[row["entity"]] else 0.0)
        for row in rows
    ]


def persist_entity_ownership(conn: duckdb.DuckDBPyConnection, *, repo_id: str, csv_text: str) -> None:
    """Update file_metrics top_owner from code-maat entity-ownership."""
    rows = parse_entity_ownership_csv(csv_text)

    by_entity: dict[str, tuple[str, float]] = {}
    for entity, author, _, pct in rows:
        if entity not in by_entity or pct > by_entity[entity][1]:
            by_entity[entity] = (author, pct)
    for entity, (author, pct) in by_entity.items():
        conn.execute(
            "UPDATE file_metrics SET top_owner_email = ?, top_owner_pct = ? "
            "WHERE repo_id = ? AND path = ?",
            [author, pct, repo_id, entity],
        )
