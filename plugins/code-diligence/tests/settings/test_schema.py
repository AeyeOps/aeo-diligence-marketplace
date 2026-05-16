import pytest
from pydantic import ValidationError

from code_diligence.settings.schema import TargetSettings


def test_minimal_valid_settings() -> None:
    s = TargetSettings(
        target_id="acme",
        target_name="Acme Corp",
        sources={"github": {"enabled": False}},
        storage={
            "warehouse_path": "~/data/code-diligence/acme.duckdb",
            "repo_clone_root": "~/data/code-diligence/repos/acme/",
            "curation_dir": "~/data/code-diligence/acme/curation/",
        },
    )
    assert s.target_id == "acme"
    assert s.sources.github.enabled is False


def test_github_enabled_requires_orgs() -> None:
    with pytest.raises(ValidationError, match="orgs"):
        TargetSettings(
            target_id="acme",
            target_name="Acme",
            sources={"github": {"enabled": True, "token_env": "TOK"}},
            storage={
                "warehouse_path": "x", "repo_clone_root": "y", "curation_dir": "z",
            },
        )


def test_github_enabled_requires_token_env() -> None:
    with pytest.raises(ValidationError, match="token_env"):
        TargetSettings(
            target_id="acme",
            target_name="Acme",
            sources={"github": {"enabled": True, "orgs": ["a"]}},
            storage={
                "warehouse_path": "x", "repo_clone_root": "y", "curation_dir": "z",
            },
        )


def test_allow_working_pattern_card_defaults_to_false() -> None:
    """75c: working-pattern card flag defaults to False (privacy gate)."""
    s = TargetSettings(
        target_id="acme",
        target_name="Acme",
        sources={"github": {"enabled": False}},
        storage={
            "warehouse_path": "x", "repo_clone_root": "y", "curation_dir": "z",
        },
    )
    assert s.heuristics.allow_working_pattern_card is False


def test_allow_working_pattern_card_can_be_enabled() -> None:
    """75c: the privacy flag is opt-in via heuristics.allow_working_pattern_card."""
    s = TargetSettings(
        target_id="acme",
        target_name="Acme",
        sources={"github": {"enabled": False}},
        storage={
            "warehouse_path": "x", "repo_clone_root": "y", "curation_dir": "z",
        },
        heuristics={"allow_working_pattern_card": True},
    )
    assert s.heuristics.allow_working_pattern_card is True


def test_target_id_kebab_case_only() -> None:
    with pytest.raises(ValidationError):
        TargetSettings(
            target_id="Acme Corp!",
            target_name="Acme",
            sources={"github": {"enabled": False}},
            storage={
                "warehouse_path": "x", "repo_clone_root": "y", "curation_dir": "z",
            },
        )
