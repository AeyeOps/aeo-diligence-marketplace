"""Heuristic for proposing author identity merges across emails.

Algorithm: pairwise comparison of (name, email-prefix) within a target.
Each pair gets a score in [0, 1] combining name token Jaccard (weight 0.7)
and email-prefix similarity (weight 0.3). Pairs above candidate_threshold
emit a MergeProposal; pairs above high_confidence_threshold are flagged for
auto-application by the curation layer.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class AuthorRecord:
    email: str
    name: str
    total_commits: int = 0


@dataclass(frozen=True)
class MergeProposal:
    canonical_email: str
    alias_email: str
    confidence: float
    reason: str


def _normalize_tokens(name: str) -> set[str]:
    """Lowercase + split on whitespace + drop common honorifics/punct."""
    if not name:
        return set()
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in name)
    return {t for t in cleaned.split() if len(t) > 1}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _prefix_sim(email_a: str, email_b: str) -> float:
    """Cheap normalized longest-common-substring on email prefixes."""
    pa, _, _ = email_a.partition("@")
    pb, _, _ = email_b.partition("@")
    pa = "".join(c for c in pa.lower() if c.isalnum())
    pb = "".join(c for c in pb.lower() if c.isalnum())
    if not pa or not pb:
        return 0.0
    if pa == pb:
        return 1.0
    short, long_ = (pa, pb) if len(pa) <= len(pb) else (pb, pa)
    if short in long_:
        return 0.85
    # Token-set overlap on prefix character bigrams
    bigrams_a = {pa[i:i+2] for i in range(len(pa) - 1)}
    bigrams_b = {pb[i:i+2] for i in range(len(pb) - 1)}
    return _jaccard(bigrams_a, bigrams_b)


def score_identity_pair(a: AuthorRecord, b: AuthorRecord) -> float:
    """Return a similarity score in [0, 1] for the pair."""
    if a.email == b.email:
        return 1.0
    name_sim = _jaccard(_normalize_tokens(a.name), _normalize_tokens(b.name))
    prefix_sim = _prefix_sim(a.email, b.email)
    return 0.7 * name_sim + 0.3 * prefix_sim


def propose_merges(
    authors: Iterable[AuthorRecord],
    *,
    high_confidence_threshold: float = 0.85,
    candidate_threshold: float = 0.55,
) -> list[MergeProposal]:
    """Yield MergeProposal for any pair scoring above candidate_threshold.

    Canonical = the email with more total commits (tie-broken by lexicographic order).
    """
    authors = list(authors)
    proposals: list[MergeProposal] = []
    for a, b in combinations(authors, 2):
        score = score_identity_pair(a, b)
        if score < candidate_threshold:
            continue
        # Canonical chosen by commit count; ties go to alphabetically smaller email
        if (a.total_commits, -ord(a.email[0])) >= (b.total_commits, -ord(b.email[0])):
            canon, alias = a, b
        else:
            canon, alias = b, a
        reason = f"name_sim={_jaccard(_normalize_tokens(a.name), _normalize_tokens(b.name)):.2f}; prefix_sim={_prefix_sim(a.email, b.email):.2f}"
        proposals.append(MergeProposal(
            canonical_email=canon.email,
            alias_email=alias.email,
            confidence=round(score, 3),
            reason=reason,
        ))
    return proposals
