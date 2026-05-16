"""Run heuristics, merge with existing YAML, write back, apply to warehouse."""
from pathlib import Path
from typing import TypeVar

import duckdb

from code_diligence.heuristics.fte import AuthorActivity, classify_all
from code_diligence.heuristics.identity import AuthorRecord, propose_merges
from code_diligence.heuristics.repo_class import RepoFacts, classify_repo

from .apply import apply_fte, apply_identity, apply_repo_class
from .merge import merge_fte, merge_identity, merge_repo
from .schema import (
    FteClassificationEntry,
    FteClassificationFile,
    IdentityMergeEntry,
    IdentityMergesFile,
    RepoClassificationEntry,
    RepoClassificationFile,
)

T = TypeVar("T", IdentityMergesFile, FteClassificationFile, RepoClassificationFile)


def _load_or_default(path: Path, cls: type[T]) -> T:
    if path.exists():
        return cls.from_yaml(path.read_text())
    return cls()


def run_curation_pass(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    target_domain: str | None,
    curation_dir: Path,
    repo_root: Path,
    abandoned_threshold_days: int,
) -> None:
    """Run identity / FTE / repo classification heuristics and persist results."""
    curation_dir.mkdir(parents=True, exist_ok=True)

    # --- Identity ---
    authors = _query_authors(conn, target_id)
    proposals_raw = propose_merges(authors)
    proposals = [
        IdentityMergeEntry(
            canonical=p.canonical_email, alias=p.alias_email,
            source="heuristic", confidence=p.confidence, reason=p.reason,
        )
        for p in proposals_raw
    ]
    id_path = curation_dir / "identity-merges.yaml"
    id_existing = _load_or_default(id_path, IdentityMergesFile)
    id_merged = merge_identity(id_existing, proposals)
    id_path.write_text(id_merged.to_yaml())
    apply_identity(conn, target_id=target_id, file=id_merged)

    # --- FTE ---
    activities = _query_activities(conn, target_id, target_domain)
    fte_classifications = [
        FteClassificationEntry(
            email=c.email, label=c.label, confidence=c.confidence,
            source="heuristic", signals=c.signals,
        )
        for c in classify_all(activities)
    ]
    fte_path = curation_dir / "fte-classification.yaml"
    fte_existing = _load_or_default(fte_path, FteClassificationFile)
    fte_merged = merge_fte(fte_existing, fte_classifications)
    fte_path.write_text(fte_merged.to_yaml())
    apply_fte(conn, target_id=target_id, file=fte_merged)

    # --- Repo class ---
    repos = _query_repo_facts(conn, target_id, repo_root)
    repo_classifications = [
        RepoClassificationEntry(
            repo_id=c.repo_id, label=c.label, confidence=c.confidence,
            source="heuristic", signals=c.signals,
        )
        for r in repos
        for c in [classify_repo(r, abandoned_threshold_days=abandoned_threshold_days)]
    ]
    rc_path = curation_dir / "repo-classification.yaml"
    rc_existing = _load_or_default(rc_path, RepoClassificationFile)
    rc_merged = merge_repo(rc_existing, repo_classifications)
    rc_path.write_text(rc_merged.to_yaml())
    apply_repo_class(conn, file=rc_merged)


def _query_authors(conn: duckdb.DuckDBPyConnection, target_id: str) -> list[AuthorRecord]:
    rows = conn.execute(
        "SELECT author_email, COALESCE(display_name, ''), total_commits "
        "FROM authors WHERE target_id = ?",
        [target_id],
    ).fetchall()
    return [AuthorRecord(email=r[0], name=r[1], total_commits=r[2]) for r in rows]


def _query_activities(
    conn: duckdb.DuckDBPyConnection,
    target_id: str,
    target_domain: str | None,
) -> list[AuthorActivity]:
    """Compute per-author activity stats for FTE classification."""
    rows = conn.execute("""
        SELECT
          a.author_email,
          COALESCE(a.display_name, ''),
          DATE_DIFF('day', a.first_seen, a.last_seen) AS tenure_days,
          a.total_commits,
          (SELECT COUNT(DISTINCT cf.repo_id) FROM commits_fact cf
            JOIN repos r ON cf.repo_id = r.repo_id
            WHERE r.target_id = ? AND cf.author_email = a.author_email) AS repos_touched,
          (SELECT AVG(CASE WHEN EXTRACT(DOW FROM cf.author_date) BETWEEN 1 AND 5 THEN 1.0 ELSE 0.0 END)
            FROM commits_fact cf JOIN repos r ON cf.repo_id = r.repo_id
            WHERE r.target_id = ? AND cf.author_email = a.author_email) AS weekday_pct
        FROM authors a WHERE a.target_id = ?
    """, [target_id, target_id, target_id]).fetchall()
    out: list[AuthorActivity] = []
    for email, name, tenure, total, breadth, weekday in rows:
        out.append(AuthorActivity(
            email=email, name=name, target_domain=target_domain,
            tenure_days=int(tenure or 0), total_commits=int(total or 0),
            repos_touched=int(breadth or 0),
            weekday_commit_pct=float(weekday or 0.0),
            burstiness=0.0,  # rough first version; refine in v2
        ))
    return out


def _query_repo_facts(
    conn: duckdb.DuckDBPyConnection,
    target_id: str,
    repo_root: Path,
) -> list[RepoFacts]:
    rows = conn.execute(
        "SELECT repo_id, name, last_commit_at FROM repos WHERE target_id = ?",
        [target_id],
    ).fetchall()
    facts: list[RepoFacts] = []
    for repo_id, name, last_commit in rows:
        repo_path = repo_root / name
        ext_loc, total = _scan_loc(repo_path)
        facts.append(RepoFacts(
            repo_id=repo_id, repo_path=repo_path,
            last_commit_at=last_commit, total_loc=total,
            file_extension_loc=ext_loc,
        ))
    return facts


def _scan_loc(repo_path: Path) -> tuple[dict[str, int], int]:
    """Cheap line-count by extension; skip binary and >1MB files."""
    ext_loc: dict[str, int] = {}
    total = 0
    for p in repo_path.rglob("*"):
        if not p.is_file() or any(part.startswith(".git") for part in p.parts):
            continue
        try:
            if p.stat().st_size > 1_000_000:
                continue
            n = sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        ext = p.suffix.lower()
        ext_loc[ext] = ext_loc.get(ext, 0) + n
        total += n
    return ext_loc, total
