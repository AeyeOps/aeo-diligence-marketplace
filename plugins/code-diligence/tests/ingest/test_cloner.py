from pathlib import Path

import pytest

from code_diligence.ingest.cloner import CloneError, clone_or_fetch


def test_clone_local_path(synthetic_target: Path, tmp_path: Path) -> None:
    src = synthetic_target / "api"
    dest = tmp_path / "clones" / "acme--api"
    head_sha = clone_or_fetch(source_url=str(src), dest=dest)
    assert dest.exists()
    assert (dest / ".git").is_dir()
    assert len(head_sha) == 40


def test_clone_idempotent_fetches(synthetic_target: Path, tmp_path: Path) -> None:
    src = synthetic_target / "api"
    dest = tmp_path / "clones" / "acme--api"
    sha1 = clone_or_fetch(source_url=str(src), dest=dest)
    sha2 = clone_or_fetch(source_url=str(src), dest=dest)
    assert sha1 == sha2


def test_clone_raises_clean_error_on_bad_url(tmp_path: Path) -> None:
    dest = tmp_path / "clones" / "broken"
    with pytest.raises(CloneError):
        clone_or_fetch(source_url="/nonexistent/path/to/repo.git", dest=dest)
