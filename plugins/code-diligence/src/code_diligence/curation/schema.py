"""Pydantic models for the three per-target curation YAML files."""
from typing import Literal, Self

import yaml
from pydantic import BaseModel, Field


CurationSource = Literal["heuristic", "analyst", "unchanged"]


class _YamlMixin:
    """Round-trip via YAML, stable key order for clean diffs."""
    def to_yaml(self: BaseModel) -> str:  # type: ignore[misc]
        # model_dump with mode='python' yields plain types yaml.safe_dump can handle
        return yaml.safe_dump(self.model_dump(mode="python"), sort_keys=False, default_flow_style=False)

    @classmethod
    def from_yaml(cls: type[Self], text: str) -> Self:
        data = yaml.safe_load(text) or {}
        return cls.model_validate(data)  # type: ignore[attr-defined]


class IdentityMergeEntry(BaseModel):
    canonical: str
    alias: str
    source: CurationSource
    confidence: float
    reason: str | None = None


class IdentityMergesFile(BaseModel, _YamlMixin):
    confirmed: list[IdentityMergeEntry] = Field(default_factory=list)
    needs_review: list[IdentityMergeEntry] = Field(default_factory=list)
    do_not_merge: list[IdentityMergeEntry] = Field(default_factory=list)


class FteClassificationEntry(BaseModel):
    email: str
    label: Literal["fte", "contractor", "bot", "unknown"]
    confidence: float
    source: CurationSource
    signals: dict[str, float] = Field(default_factory=dict)


class FteClassificationFile(BaseModel, _YamlMixin):
    confirmed: list[FteClassificationEntry] = Field(default_factory=list)
    needs_review: list[FteClassificationEntry] = Field(default_factory=list)


class RepoClassificationEntry(BaseModel):
    repo_id: str
    label: Literal["production", "tooling", "experiment", "abandoned", "docs", "fork", "unknown"]
    confidence: float
    source: CurationSource
    signals: dict[str, float | bool] = Field(default_factory=dict)


class RepoClassificationFile(BaseModel, _YamlMixin):
    confirmed: list[RepoClassificationEntry] = Field(default_factory=list)
    needs_review: list[RepoClassificationEntry] = Field(default_factory=list)
