from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from code_diligence.heuristics.repo_class import (
    RepoFacts,
    classify_repo,
    _signal_is_fork,
    _signal_has_ci,
    _signal_has_tests,
    _signal_recency,
    _signal_docs_dominant,
)


_UNSET: object = object()


def _facts(
    tmp_path: Path,
    *,
    repo_id: str = "acme/svc",
    last_commit_at: datetime | None | object = _UNSET,
    total_loc: int = 8000,
    file_extension_loc: dict[str, int] | None = None,
) -> RepoFacts:
    if last_commit_at is _UNSET:
        last_commit_at = datetime.now(timezone.utc) - timedelta(days=10)
    if file_extension_loc is None:
        file_extension_loc = {".py": total_loc}
    return RepoFacts(
        repo_id=repo_id,
        repo_path=tmp_path,
        last_commit_at=last_commit_at,
        total_loc=total_loc,
        file_extension_loc=file_extension_loc,
    )


def test_signal_is_fork_true(tmp_path: Path) -> None:
    (tmp_path / ".fork-of").write_text("upstream/repo")
    assert _signal_is_fork(_facts(tmp_path)) is True


def test_signal_is_fork_false(tmp_path: Path) -> None:
    assert _signal_is_fork(_facts(tmp_path)) is False


def test_signal_has_ci_github_workflows(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    assert _signal_has_ci(_facts(tmp_path)) is True


def test_signal_has_ci_false(tmp_path: Path) -> None:
    assert _signal_has_ci(_facts(tmp_path)) is False


def test_signal_has_tests_dir(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    assert _signal_has_tests(_facts(tmp_path)) is True


def test_signal_has_tests_false(tmp_path: Path) -> None:
    assert _signal_has_tests(_facts(tmp_path)) is False


def test_signal_recency_recent(tmp_path: Path) -> None:
    f = _facts(tmp_path, last_commit_at=datetime.now(timezone.utc) - timedelta(days=30))
    assert _signal_recency(f, abandoned_threshold_days=180) == 1.0


def test_signal_recency_abandoned(tmp_path: Path) -> None:
    f = _facts(tmp_path, last_commit_at=datetime.now(timezone.utc) - timedelta(days=400))
    assert _signal_recency(f, abandoned_threshold_days=180) == 0.0


def test_signal_recency_none(tmp_path: Path) -> None:
    f = _facts(tmp_path, last_commit_at=None)
    assert _signal_recency(f, abandoned_threshold_days=180) == 0.0


def test_signal_docs_dominant(tmp_path: Path) -> None:
    f = _facts(tmp_path, total_loc=1000, file_extension_loc={".md": 900, ".py": 100})
    assert _signal_docs_dominant(f) == pytest.approx(0.9)


def test_signal_docs_dominant_zero_total(tmp_path: Path) -> None:
    f = _facts(tmp_path, total_loc=0, file_extension_loc={})
    assert _signal_docs_dominant(f) == 0.0


def test_classify_production(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    result = classify_repo(_facts(tmp_path, total_loc=8000))
    assert result.label == "production"
    assert result.confidence >= 0.85


def test_classify_tooling(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    result = classify_repo(_facts(tmp_path, total_loc=500))
    assert result.label == "tooling"
    assert result.confidence >= 0.7


def test_classify_experiment(tmp_path: Path) -> None:
    # Recent + no CI + no tests + LOC > 1000 → experiment
    result = classify_repo(_facts(tmp_path, total_loc=1500))
    assert result.label == "experiment"
    assert result.confidence >= 0.6


def test_classify_abandoned(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    result = classify_repo(_facts(
        tmp_path, total_loc=8000,
        last_commit_at=datetime.now(timezone.utc) - timedelta(days=400),
    ))
    assert result.label == "abandoned"
    assert result.confidence >= 0.9


def test_classify_docs(tmp_path: Path) -> None:
    result = classify_repo(_facts(
        tmp_path, total_loc=400,
        file_extension_loc={".md": 380, ".py": 20},
    ))
    assert result.label == "docs"
    assert result.confidence >= 0.85


def test_classify_fork(tmp_path: Path) -> None:
    (tmp_path / ".fork-of").write_text("upstream/repo")
    # Even with FTE-like signals, fork marker dominates
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    result = classify_repo(_facts(tmp_path, total_loc=8000))
    assert result.label == "fork"
    assert result.confidence >= 0.95
