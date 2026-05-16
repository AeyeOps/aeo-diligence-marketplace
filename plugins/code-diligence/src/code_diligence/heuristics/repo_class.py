"""Heuristic for classifying repos as production / tooling / experiment / abandoned / docs / fork / unknown.

Signals: last-commit recency, CI presence, test-dir presence, docs dominance,
fork marker, and total LOC. Marker-based classes (fork, docs, abandoned)
short-circuit; remaining classes fall out of CI/tests/LOC combinations.
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

ClassLabel = Literal["production", "tooling", "experiment", "abandoned", "docs", "fork", "unknown"]


@dataclass(frozen=True)
class RepoFacts:
    repo_id: str
    repo_path: Path
    last_commit_at: datetime | None
    total_loc: int
    file_extension_loc: dict[str, int]   # {".py": 3000, ".md": 200, ...}


@dataclass(frozen=True)
class RepoClassification:
    repo_id: str
    label: ClassLabel
    confidence: float
    signals: dict[str, float | bool]


_CI_MARKERS = (
    Path(".github/workflows"), Path(".gitlab-ci.yml"),
    Path(".circleci/config.yml"), Path("Jenkinsfile"),
)
_TEST_DIRS = ("tests", "test", "spec", "__tests__")
_DOCS_EXTS = {".md", ".rst", ".txt", ".adoc"}


def _signal_is_fork(facts: RepoFacts) -> bool:
    return (facts.repo_path / ".fork-of").exists()


def _signal_has_ci(facts: RepoFacts) -> bool:
    return any((facts.repo_path / m).exists() for m in _CI_MARKERS)


def _signal_has_tests(facts: RepoFacts) -> bool:
    return any((facts.repo_path / d).is_dir() for d in _TEST_DIRS)


def _signal_recency(facts: RepoFacts, abandoned_threshold_days: int) -> float:
    """1.0 if commit in last 90d; 0.0 if older than abandoned_threshold_days."""
    if facts.last_commit_at is None:
        return 0.0
    age_days = (datetime.now(UTC) - facts.last_commit_at.astimezone(UTC)).days
    if age_days <= 90:
        return 1.0
    if age_days >= abandoned_threshold_days:
        return 0.0
    return 1.0 - (age_days - 90) / (abandoned_threshold_days - 90)


def _signal_docs_dominant(facts: RepoFacts) -> float:
    if facts.total_loc == 0:
        return 0.0
    docs_loc = sum(loc for ext, loc in facts.file_extension_loc.items() if ext in _DOCS_EXTS)
    return docs_loc / facts.total_loc


def classify_repo(facts: RepoFacts, *, abandoned_threshold_days: int = 180) -> RepoClassification:
    sig: dict[str, float | bool] = {}

    # Marker-based classes win when present
    sig["is_fork"] = _signal_is_fork(facts)
    if sig["is_fork"]:
        return RepoClassification(facts.repo_id, "fork", 0.95, sig)

    sig["docs_dominant"] = round(_signal_docs_dominant(facts), 3)
    if sig["docs_dominant"] >= 0.8 and facts.total_loc < 2000:
        return RepoClassification(facts.repo_id, "docs", 0.9, sig)

    sig["recency"] = round(_signal_recency(facts, abandoned_threshold_days), 3)
    if sig["recency"] == 0.0:
        return RepoClassification(facts.repo_id, "abandoned", 0.95, sig)

    sig["has_ci"] = _signal_has_ci(facts)
    sig["has_tests"] = _signal_has_tests(facts)
    sig["loc"] = float(facts.total_loc)

    if sig["has_ci"] and sig["has_tests"] and facts.total_loc > 5000:
        return RepoClassification(facts.repo_id, "production", 0.9, sig)
    if sig["has_ci"] and sig["has_tests"]:
        return RepoClassification(facts.repo_id, "tooling", 0.75, sig)
    if facts.total_loc > 1000:
        return RepoClassification(facts.repo_id, "experiment", 0.6, sig)
    return RepoClassification(facts.repo_id, "unknown", 0.4, sig)
