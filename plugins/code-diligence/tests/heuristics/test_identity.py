from code_diligence.heuristics.identity import (
    score_identity_pair, propose_merges, AuthorRecord,
)


def _ar(email: str, name: str) -> AuthorRecord:
    return AuthorRecord(email=email, name=name, total_commits=10)


def test_score_high_for_same_name_different_email() -> None:
    score = score_identity_pair(
        _ar("pat@acme.com", "Pat Smith"),
        _ar("pat@gmail.com", "Pat Smith"),
    )
    assert score >= 0.85


def test_score_medium_for_partial_name_match() -> None:
    score = score_identity_pair(
        _ar("pat@acme.com", "Pat Smith"),
        _ar("pat@gmail.com", "Pat S"),
    )
    assert 0.55 <= score < 0.85


def test_score_low_for_different_name_same_prefix() -> None:
    # Same email prefix "pat" but completely different names — coincidence, low score
    score = score_identity_pair(
        _ar("pat@acme.com", "Pat Smith"),
        _ar("pat@beta.com", "Patricia Park"),
    )
    assert score < 0.55


def test_score_zero_for_unrelated() -> None:
    score = score_identity_pair(
        _ar("alice@acme.com", "Alice Wong"),
        _ar("bob@acme.com", "Bob Smith"),
    )
    assert score < 0.2


def test_propose_merges_groups_high_confidence() -> None:
    authors = [
        _ar("pat@acme.com", "Pat Smith"),
        _ar("pat@gmail.com", "Pat Smith"),
        _ar("mike@acme.com", "Mike Brown"),
        _ar("alice@acme.com", "Alice Wong"),
    ]
    proposals = propose_merges(authors, high_confidence_threshold=0.85, candidate_threshold=0.55)
    # Should propose merging the two pats with high confidence
    high = [p for p in proposals if p.confidence >= 0.85]
    assert len(high) == 1
    assert {high[0].canonical_email, high[0].alias_email} == {"pat@acme.com", "pat@gmail.com"}
    # Mike and Alice are not merge candidates
    others = [p for p in proposals if p.confidence < 0.85]
    assert all(p.alias_email not in {"mike@acme.com", "alice@acme.com"} for p in others)


def test_canonical_chosen_by_total_commits() -> None:
    a = AuthorRecord(email="pat@acme.com", name="Pat S", total_commits=100)
    b = AuthorRecord(email="pat@gmail.com", name="Pat S", total_commits=5)
    proposals = propose_merges([a, b], high_confidence_threshold=0.85, candidate_threshold=0.55)
    assert len(proposals) == 1
    assert proposals[0].canonical_email == "pat@acme.com"  # more commits wins
    assert proposals[0].alias_email == "pat@gmail.com"
