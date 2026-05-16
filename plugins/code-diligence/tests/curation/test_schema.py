from code_diligence.curation.schema import (
    IdentityMergesFile, IdentityMergeEntry,
    FteClassificationFile, FteClassificationEntry,
    RepoClassificationFile, RepoClassificationEntry,
)


def test_identity_merges_round_trip() -> None:
    f = IdentityMergesFile(
        confirmed=[IdentityMergeEntry(canonical="pat@acme.com", alias="pat@gmail.com", source="heuristic", confidence=0.92)],
        needs_review=[IdentityMergeEntry(canonical="alice@acme.com", alias="alice@beta.com", source="heuristic", confidence=0.6)],
        do_not_merge=[],
    )
    yaml_text = f.to_yaml()
    parsed = IdentityMergesFile.from_yaml(yaml_text)
    assert parsed == f


def test_fte_classification_round_trip() -> None:
    f = FteClassificationFile(
        confirmed=[FteClassificationEntry(email="pat@acme.com", label="fte", confidence=0.9, source="heuristic", signals={"domain": 1.0})],
        needs_review=[],
    )
    parsed = FteClassificationFile.from_yaml(f.to_yaml())
    assert parsed == f


def test_repo_classification_round_trip() -> None:
    f = RepoClassificationFile(
        confirmed=[RepoClassificationEntry(repo_id="acme/api", label="production", confidence=0.9, source="heuristic")],
        needs_review=[],
    )
    parsed = RepoClassificationFile.from_yaml(f.to_yaml())
    assert parsed == f


def test_analyst_source_marks_persistence() -> None:
    """Entries with source='analyst' must be preserved across rewrites."""
    f = IdentityMergesFile(
        confirmed=[IdentityMergeEntry(canonical="x@a", alias="y@a", source="analyst", confidence=1.0)],
        needs_review=[], do_not_merge=[],
    )
    parsed = IdentityMergesFile.from_yaml(f.to_yaml())
    assert parsed.confirmed[0].source == "analyst"
