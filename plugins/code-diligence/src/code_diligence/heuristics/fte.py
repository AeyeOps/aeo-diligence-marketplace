"""Heuristic for classifying authors as FTE / contractor / bot / unknown.

Signals: email domain match, commit cadence (weekday share + steadiness),
tenure (days active), repo breadth (count of repos touched). A separate
bot detector short-circuits on common automation markers.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

ClassLabel = Literal["fte", "contractor", "bot", "unknown"]


@dataclass(frozen=True)
class AuthorActivity:
    email: str
    name: str
    target_domain: str | None         # e.g. "acme.com"
    tenure_days: int                  # last_seen - first_seen
    total_commits: int
    repos_touched: int
    weekday_commit_pct: float         # 0.0 to 1.0; M-F share
    burstiness: float                 # 0.0 (steady) to 1.0 (one big burst)


@dataclass(frozen=True)
class FteClassification:
    email: str
    label: ClassLabel
    confidence: float
    signals: dict[str, float]         # individual signal scores for transparency


_BOT_MARKERS = ("[bot]", "@dependabot.com", "renovate[bot]", "github-actions[bot]")


def _signal_bot(a: AuthorActivity) -> float:
    """1.0 if email or name strongly indicates bot."""
    blob = (a.email + " " + a.name).lower()
    return 1.0 if any(m in blob for m in _BOT_MARKERS) else 0.0


def _signal_domain(a: AuthorActivity) -> float:
    """1.0 if email domain matches target_domain; 0.1 for known free providers; 0.4 otherwise."""
    if not a.target_domain:
        return 0.5
    domain = a.email.partition("@")[2].lower()
    if domain == a.target_domain.lower():
        return 1.0
    if domain in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "users.noreply.github.com"}:
        return 0.1
    return 0.4


def _signal_cadence(a: AuthorActivity) -> float:
    """Higher = more FTE-like (steady weekday cadence). Combines weekday_pct and inverse burstiness."""
    return 0.6 * a.weekday_commit_pct + 0.4 * (1.0 - a.burstiness)


def _signal_tenure(a: AuthorActivity) -> float:
    """1.0 at >365 days, 0.1 at <30 days, linear in between."""
    if a.tenure_days >= 365:
        return 1.0
    if a.tenure_days <= 30:
        return 0.1
    return 0.1 + 0.9 * (a.tenure_days - 30) / (365 - 30)


def _signal_breadth(a: AuthorActivity) -> float:
    """1.0 at >=10 repos, 0.1 at 1 repo, log-ish in between."""
    if a.repos_touched <= 1:
        return 0.1
    if a.repos_touched >= 10:
        return 1.0
    return 0.1 + 0.9 * (a.repos_touched - 1) / 9


def classify(a: AuthorActivity) -> FteClassification:
    bot = _signal_bot(a)
    if bot >= 1.0:
        return FteClassification(
            email=a.email, label="bot", confidence=0.95,
            signals={"bot": bot},
        )
    domain = _signal_domain(a)
    cadence = _signal_cadence(a)
    tenure = _signal_tenure(a)
    breadth = _signal_breadth(a)
    fte_score = 0.35 * domain + 0.25 * cadence + 0.25 * tenure + 0.15 * breadth
    contractor_score = 0.35 * (1 - domain) + 0.25 * (1 - cadence) + 0.25 * (1 - tenure) + 0.15 * (1 - breadth)
    signals = {"domain": domain, "cadence": cadence, "tenure": tenure, "breadth": breadth}
    if fte_score >= 0.7 and fte_score - contractor_score >= 0.2:
        return FteClassification(email=a.email, label="fte", confidence=round(fte_score, 3), signals=signals)
    if contractor_score >= 0.7 and contractor_score - fte_score >= 0.2:
        return FteClassification(email=a.email, label="contractor", confidence=round(contractor_score, 3), signals=signals)
    return FteClassification(email=a.email, label="unknown", confidence=round(max(fte_score, contractor_score), 3), signals=signals)


def classify_all(activities: Iterable[AuthorActivity]) -> list[FteClassification]:
    return [classify(a) for a in activities]
