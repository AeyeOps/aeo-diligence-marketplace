from code_diligence.curation.merge import merge_identity, merge_fte, merge_repo
from code_diligence.curation.schema import (
    IdentityMergesFile, IdentityMergeEntry,
    FteClassificationFile, FteClassificationEntry,
    RepoClassificationFile, RepoClassificationEntry,
)


# ---------- merge_identity ----------

def test_merge_identity_preserves_analyst_confirmed() -> None:
    existing = IdentityMergesFile(
        confirmed=[IdentityMergeEntry(
            canonical="pat@acme.com", alias="pat@gmail.com",
            source="analyst", confidence=1.0,
        )],
        needs_review=[], do_not_merge=[],
    )
    new_proposals = [
        # Heuristic re-proposes same pair with lower confidence — must not overwrite
        IdentityMergeEntry(
            canonical="pat@acme.com", alias="pat@gmail.com",
            source="heuristic", confidence=0.6,
        ),
    ]
    out = merge_identity(existing, new_proposals)
    assert len(out.confirmed) == 1
    assert out.confirmed[0].source == "analyst"
    assert out.confirmed[0].confidence == 1.0


def test_merge_identity_do_not_merge_blocks_reproposal() -> None:
    existing = IdentityMergesFile(
        confirmed=[], needs_review=[],
        do_not_merge=[IdentityMergeEntry(
            canonical="pat@acme.com", alias="patrick@beta.com",
            source="analyst", confidence=1.0,
        )],
    )
    new_proposals = [
        IdentityMergeEntry(
            canonical="pat@acme.com", alias="patrick@beta.com",
            source="heuristic", confidence=0.95,
        ),
    ]
    out = merge_identity(existing, new_proposals)
    assert out.confirmed == []
    assert out.needs_review == []
    assert len(out.do_not_merge) == 1


def test_merge_identity_high_confidence_goes_to_confirmed() -> None:
    existing = IdentityMergesFile(confirmed=[], needs_review=[], do_not_merge=[])
    new_proposals = [
        IdentityMergeEntry(
            canonical="a@x", alias="a@y",
            source="heuristic", confidence=0.92,
        ),
    ]
    out = merge_identity(existing, new_proposals, auto_confirm_threshold=0.85)
    assert len(out.confirmed) == 1
    assert out.confirmed[0].source == "heuristic"
    assert out.needs_review == []


def test_merge_identity_low_confidence_goes_to_needs_review() -> None:
    existing = IdentityMergesFile(confirmed=[], needs_review=[], do_not_merge=[])
    new_proposals = [
        IdentityMergeEntry(
            canonical="a@x", alias="a@y",
            source="heuristic", confidence=0.6,
        ),
    ]
    out = merge_identity(existing, new_proposals, auto_confirm_threshold=0.85)
    assert out.confirmed == []
    assert len(out.needs_review) == 1


def test_merge_identity_promotes_heuristic_review_at_higher_confidence() -> None:
    existing = IdentityMergesFile(
        confirmed=[],
        needs_review=[IdentityMergeEntry(
            canonical="a@x", alias="a@y",
            source="heuristic", confidence=0.6,
        )],
        do_not_merge=[],
    )
    new_proposals = [
        IdentityMergeEntry(
            canonical="a@x", alias="a@y",
            source="heuristic", confidence=0.95,
        ),
    ]
    out = merge_identity(existing, new_proposals, auto_confirm_threshold=0.85)
    assert len(out.confirmed) == 1
    assert out.confirmed[0].confidence == 0.95
    assert out.needs_review == []


def test_merge_identity_does_not_promote_analyst_review() -> None:
    existing = IdentityMergesFile(
        confirmed=[],
        needs_review=[IdentityMergeEntry(
            canonical="a@x", alias="a@y",
            source="analyst", confidence=0.5,
        )],
        do_not_merge=[],
    )
    new_proposals = [
        IdentityMergeEntry(
            canonical="a@x", alias="a@y",
            source="heuristic", confidence=0.95,
        ),
    ]
    out = merge_identity(existing, new_proposals, auto_confirm_threshold=0.85)
    # Analyst kept it in review — heuristic does not override
    assert out.confirmed == []
    assert len(out.needs_review) == 1
    assert out.needs_review[0].source == "analyst"


# ---------- merge_fte ----------

def test_merge_fte_preserves_analyst_confirmed() -> None:
    existing = FteClassificationFile(
        confirmed=[FteClassificationEntry(
            email="alice@acme.com", label="fte", confidence=1.0,
            source="analyst", signals={},
        )],
        needs_review=[],
    )
    new = [FteClassificationEntry(
        email="alice@acme.com", label="contractor", confidence=0.9,
        source="heuristic", signals={"domain": 0.4},
    )]
    out = merge_fte(existing, new)
    assert len(out.confirmed) == 1
    assert out.confirmed[0].source == "analyst"
    assert out.confirmed[0].label == "fte"


def test_merge_fte_high_confidence_confirmed() -> None:
    existing = FteClassificationFile(confirmed=[], needs_review=[])
    new = [FteClassificationEntry(
        email="alice@acme.com", label="fte", confidence=0.9,
        source="heuristic", signals={},
    )]
    out = merge_fte(existing, new, auto_confirm_threshold=0.8)
    assert len(out.confirmed) == 1


def test_merge_fte_low_confidence_to_review() -> None:
    existing = FteClassificationFile(confirmed=[], needs_review=[])
    new = [FteClassificationEntry(
        email="alice@acme.com", label="unknown", confidence=0.5,
        source="heuristic", signals={},
    )]
    out = merge_fte(existing, new, auto_confirm_threshold=0.8)
    assert out.confirmed == []
    assert len(out.needs_review) == 1


# ---------- merge_repo ----------

def test_merge_repo_preserves_analyst_confirmed() -> None:
    existing = RepoClassificationFile(
        confirmed=[RepoClassificationEntry(
            repo_id="acme/api", label="production", confidence=1.0,
            source="analyst", signals={},
        )],
        needs_review=[],
    )
    new = [RepoClassificationEntry(
        repo_id="acme/api", label="experiment", confidence=0.9,
        source="heuristic", signals={},
    )]
    out = merge_repo(existing, new)
    assert len(out.confirmed) == 1
    assert out.confirmed[0].source == "analyst"
    assert out.confirmed[0].label == "production"


def test_merge_repo_new_high_confidence_confirmed() -> None:
    existing = RepoClassificationFile(confirmed=[], needs_review=[])
    new = [RepoClassificationEntry(
        repo_id="acme/api", label="production", confidence=0.9,
        source="heuristic", signals={},
    )]
    out = merge_repo(existing, new, auto_confirm_threshold=0.8)
    assert len(out.confirmed) == 1


def test_merge_repo_new_low_confidence_review() -> None:
    existing = RepoClassificationFile(confirmed=[], needs_review=[])
    new = [RepoClassificationEntry(
        repo_id="acme/api", label="unknown", confidence=0.5,
        source="heuristic", signals={},
    )]
    out = merge_repo(existing, new, auto_confirm_threshold=0.8)
    assert out.confirmed == []
    assert len(out.needs_review) == 1
