from pathlib import Path

import pytest

from code_diligence.settings.loader import load_target_settings, resolve_token

VALID_FILE = """---
target_id: acme-corp
target_name: Acme Corp
description: Test target
---
sources:
  github:
    enabled: true
    token_env: TEST_TOKEN_ENV_VAR
    orgs: [acme-corp]
storage:
  warehouse_path: ~/data/code-diligence/acme-corp.duckdb
  repo_clone_root: ~/data/code-diligence/repos/acme-corp/
  curation_dir: ~/data/code-diligence/acme-corp/curation/
"""


def test_load_valid_settings(tmp_path: Path) -> None:
    f = tmp_path / "code-diligence-acme-corp.local.md"
    f.write_text(VALID_FILE)
    s = load_target_settings(f)
    assert s.target_id == "acme-corp"
    assert s.target_name == "Acme Corp"
    assert s.sources.github.enabled is True
    assert s.sources.github.orgs == ["acme-corp"]


def test_load_rejects_missing_frontmatter(tmp_path: Path) -> None:
    f = tmp_path / "bad.local.md"
    f.write_text("sources: {}\nstorage: {warehouse_path: x, repo_clone_root: y, curation_dir: z}\n")
    with pytest.raises(ValueError, match="frontmatter"):
        load_target_settings(f)


def test_resolve_token_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_TOKEN", "ghp_secret")
    assert resolve_token("MY_TOKEN") == "ghp_secret"


def test_resolve_token_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="MISSING_TOKEN"):
        resolve_token("MISSING_TOKEN")
