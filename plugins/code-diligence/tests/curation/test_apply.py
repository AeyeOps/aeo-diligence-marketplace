import json
from pathlib import Path

from code_diligence.curation.apply import (
    apply_fte,
    apply_identity,
    apply_repo_class,
)
from code_diligence.curation.schema import (
    FteClassificationEntry,
    FteClassificationFile,
    IdentityMergeEntry,
    IdentityMergesFile,
    RepoClassificationEntry,
    RepoClassificationFile,
)
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target


def test_apply_identity_writes_identity_map(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        f = IdentityMergesFile(
            confirmed=[IdentityMergeEntry(
                canonical="pat@acme.com", alias="pat@gmail.com",
                source="heuristic", confidence=0.9,
            )],
            needs_review=[], do_not_merge=[],
        )
        apply_identity(conn, target_id="acme", file=f)
        rows = conn.execute(
            "SELECT raw_email, canonical_email, source FROM identity_map "
            "WHERE target_id='acme' ORDER BY raw_email"
        ).fetchall()
    # Alias maps to canonical, plus self-mapping for canonical
    assert ("pat@gmail.com", "pat@acme.com", "heuristic") in rows
    assert ("pat@acme.com", "pat@acme.com", "unchanged") in rows


def test_apply_identity_replaces_previous_rows(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        first = IdentityMergesFile(
            confirmed=[IdentityMergeEntry(
                canonical="a@x", alias="a@y",
                source="heuristic", confidence=0.9,
            )],
            needs_review=[], do_not_merge=[],
        )
        apply_identity(conn, target_id="acme", file=first)
        # Second apply with different mapping replaces first
        second = IdentityMergesFile(
            confirmed=[IdentityMergeEntry(
                canonical="b@x", alias="b@y",
                source="heuristic", confidence=0.9,
            )],
            needs_review=[], do_not_merge=[],
        )
        apply_identity(conn, target_id="acme", file=second)
        rows = conn.execute(
            "SELECT raw_email FROM identity_map WHERE target_id='acme' ORDER BY raw_email"
        ).fetchall()
    raw = {r[0] for r in rows}
    assert raw == {"b@x", "b@y"}


def test_apply_fte_writes_contributor_classification(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        f = FteClassificationFile(
            confirmed=[FteClassificationEntry(
                email="alice@acme.com", label="fte", confidence=0.9,
                source="heuristic", signals={"domain": 1.0, "cadence": 0.9},
            )],
            needs_review=[],
        )
        apply_fte(conn, target_id="acme", file=f)
        rows = conn.execute(
            "SELECT author_email, class, confidence, signals, source "
            "FROM contributor_classification WHERE target_id='acme'"
        ).fetchall()
    assert len(rows) == 1
    email, label, conf, signals, source = rows[0]
    assert email == "alice@acme.com"
    assert label == "fte"
    assert conf == 0.9
    assert source == "heuristic"
    # signals is JSON-encoded; DuckDB JSON type returns a string
    parsed_signals = json.loads(signals) if isinstance(signals, str) else signals
    assert parsed_signals["domain"] == 1.0


def test_apply_repo_class_writes_repo_classification(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    with open_warehouse(db) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url="local")
        f = RepoClassificationFile(
            confirmed=[RepoClassificationEntry(
                repo_id="acme/api", label="production", confidence=0.9,
                source="heuristic", signals={"has_ci": True, "loc": 8000.0},
            )],
            needs_review=[],
        )
        apply_repo_class(conn, file=f)
        rows = conn.execute(
            "SELECT repo_id, class, confidence, source FROM repo_classification"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0] == ("acme/api", "production", 0.9, "heuristic")
