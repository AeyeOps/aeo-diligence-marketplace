"""Load curation YAML 'confirmed' entries into warehouse curation tables."""
import json

import duckdb

from .schema import (
    FteClassificationFile,
    IdentityMergesFile,
    RepoClassificationFile,
)


def apply_identity(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    file: IdentityMergesFile,
) -> None:
    """Replace identity_map for target_id with the file's confirmed entries.

    For each confirmed pair, write the alias→canonical mapping and a
    canonical→canonical self-mapping so joins always have a base row.
    """
    destinations: dict[str, set[str]] = {}
    entries = {}
    for entry in file.confirmed:
        destinations.setdefault(entry.alias, set()).add(entry.canonical)
        entries[entry.alias] = entry

    def resolve(email: str, visiting: frozenset[str] = frozenset()) -> str:
        if email in visiting:
            raise ValueError(f"identity merge cycle at {email}")
        targets = destinations.get(email, {email}) - {email}
        if not targets:
            return email
        roots = {resolve(target, visiting | {email}) for target in targets}
        if len(roots) != 1:
            raise ValueError(f"conflicting canonical identities for {email}")
        return roots.pop()

    resolved = {email: resolve(email) for email in destinations}
    for canonical in tuple(resolved.values()):
        resolved[canonical] = canonical
    rows = [
        (target_id, email, canonical,
         entries[email].confidence if email in entries else 1.0,
         entries[email].source if email in entries else "unchanged")
        for email, canonical in sorted(resolved.items())
    ]
    conn.execute("DELETE FROM identity_map WHERE target_id = ?", [target_id])
    if rows:
        conn.executemany(
            "INSERT INTO identity_map (target_id, raw_email, canonical_email, confidence, source) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )


def apply_fte(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_id: str,
    file: FteClassificationFile,
) -> None:
    """Replace contributor_classification for target_id with confirmed entries."""
    conn.execute(
        "DELETE FROM contributor_classification WHERE target_id = ?",
        [target_id],
    )
    rows = [
        (target_id, e.email, e.label, e.confidence, json.dumps(e.signals), e.source)
        for e in file.confirmed
    ]
    if rows:
        conn.executemany(
            "INSERT INTO contributor_classification "
            "(target_id, author_email, class, confidence, signals, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )


def apply_repo_class(
    conn: duckdb.DuckDBPyConnection,
    *,
    file: RepoClassificationFile,
) -> None:
    """Replace repo_classification rows for the repos in the file's confirmed list."""
    repo_ids = [e.repo_id for e in file.confirmed]
    if repo_ids:
        placeholders = ",".join(["?"] * len(repo_ids))
        conn.execute(
            f"DELETE FROM repo_classification WHERE repo_id IN ({placeholders})",
            repo_ids,
        )
    rows = [
        (e.repo_id, e.label, e.confidence, json.dumps(e.signals), e.source)
        for e in file.confirmed
    ]
    if rows:
        conn.executemany(
            "INSERT INTO repo_classification (repo_id, class, confidence, signals, source) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
