"""Merge new heuristic candidates with existing analyst-edited curation files.

Each merge function preserves analyst-confirmed and analyst-held-in-review
entries, while letting fresh heuristic candidates flow into `confirmed` or
`needs_review` based on a confidence threshold.
"""
from .schema import (
    FteClassificationEntry,
    FteClassificationFile,
    IdentityMergeEntry,
    IdentityMergesFile,
    RepoClassificationEntry,
    RepoClassificationFile,
)


def merge_identity(
    existing: IdentityMergesFile,
    new_proposals: list[IdentityMergeEntry],
    *,
    auto_confirm_threshold: float = 0.85,
) -> IdentityMergesFile:
    """Merge new identity-merge proposals with an existing file."""
    blocked = {(e.canonical, e.alias) for e in existing.do_not_merge}
    by_pair_confirmed = {(e.canonical, e.alias): e for e in existing.confirmed}
    by_pair_review = {(e.canonical, e.alias): e for e in existing.needs_review}

    confirmed: list[IdentityMergeEntry] = list(existing.confirmed)
    needs_review: list[IdentityMergeEntry] = []
    seen: set[tuple[str, str]] = set(by_pair_confirmed.keys())

    for prop in new_proposals:
        key = (prop.canonical, prop.alias)
        if key in blocked:
            continue
        if key in by_pair_confirmed:
            continue
        if key in by_pair_review:
            existing_entry = by_pair_review[key]
            if existing_entry.source == "analyst":
                needs_review.append(existing_entry)
                seen.add(key)
                continue
            seen.add(key)
            if prop.confidence >= auto_confirm_threshold:
                confirmed.append(prop)
            else:
                needs_review.append(prop)
            continue
        seen.add(key)
        if prop.confidence >= auto_confirm_threshold:
            confirmed.append(prop)
        else:
            needs_review.append(prop)

    # Carry over any review entries that weren't re-proposed (heuristic regressed)
    for key, entry in by_pair_review.items():
        if key not in seen:
            needs_review.append(entry)

    return IdentityMergesFile(
        confirmed=confirmed,
        needs_review=needs_review,
        do_not_merge=list(existing.do_not_merge),
    )


def merge_fte(
    existing: FteClassificationFile,
    new_classifications: list[FteClassificationEntry],
    *,
    auto_confirm_threshold: float = 0.8,
) -> FteClassificationFile:
    """Merge new FTE classifications with an existing file (keyed by email)."""
    by_email_confirmed = {e.email: e for e in existing.confirmed}
    by_email_review = {e.email: e for e in existing.needs_review}

    confirmed: list[FteClassificationEntry] = list(existing.confirmed)
    needs_review: list[FteClassificationEntry] = []
    seen: set[str] = set(by_email_confirmed.keys())

    for prop in new_classifications:
        if prop.email in by_email_confirmed:
            continue
        if prop.email in by_email_review:
            existing_entry = by_email_review[prop.email]
            if existing_entry.source == "analyst":
                needs_review.append(existing_entry)
                seen.add(prop.email)
                continue
            seen.add(prop.email)
            if prop.confidence >= auto_confirm_threshold:
                confirmed.append(prop)
            else:
                needs_review.append(prop)
            continue
        seen.add(prop.email)
        if prop.confidence >= auto_confirm_threshold:
            confirmed.append(prop)
        else:
            needs_review.append(prop)

    for email, entry in by_email_review.items():
        if email not in seen:
            needs_review.append(entry)

    return FteClassificationFile(confirmed=confirmed, needs_review=needs_review)


def merge_repo(
    existing: RepoClassificationFile,
    new_classifications: list[RepoClassificationEntry],
    *,
    auto_confirm_threshold: float = 0.8,
) -> RepoClassificationFile:
    """Merge new repo classifications with an existing file (keyed by repo_id)."""
    by_id_confirmed = {e.repo_id: e for e in existing.confirmed}
    by_id_review = {e.repo_id: e for e in existing.needs_review}

    confirmed: list[RepoClassificationEntry] = list(existing.confirmed)
    needs_review: list[RepoClassificationEntry] = []
    seen: set[str] = set(by_id_confirmed.keys())

    for prop in new_classifications:
        if prop.repo_id in by_id_confirmed:
            continue
        if prop.repo_id in by_id_review:
            existing_entry = by_id_review[prop.repo_id]
            if existing_entry.source == "analyst":
                needs_review.append(existing_entry)
                seen.add(prop.repo_id)
                continue
            seen.add(prop.repo_id)
            if prop.confidence >= auto_confirm_threshold:
                confirmed.append(prop)
            else:
                needs_review.append(prop)
            continue
        seen.add(prop.repo_id)
        if prop.confidence >= auto_confirm_threshold:
            confirmed.append(prop)
        else:
            needs_review.append(prop)

    for repo_id, entry in by_id_review.items():
        if repo_id not in seen:
            needs_review.append(entry)

    return RepoClassificationFile(confirmed=confirmed, needs_review=needs_review)
