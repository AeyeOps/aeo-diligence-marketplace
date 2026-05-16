"""Pydantic models for per-target settings."""
import re
from typing import Self

from pydantic import BaseModel, Field, model_validator

_TARGET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


class GitHubSource(BaseModel):
    enabled: bool = False
    token_env: str | None = None
    orgs: list[str] = Field(default_factory=list)
    include_archived: bool = False

    @model_validator(mode="after")
    def _require_token_and_orgs_when_enabled(self) -> Self:
        if self.enabled:
            if not self.token_env:
                raise ValueError("github.token_env is required when github.enabled is true")
            if not self.orgs:
                raise ValueError("github.orgs is required (non-empty) when github.enabled is true")
        return self


class GitHubPlatformSource(BaseModel):
    pr_data: bool = False
    actions_data: bool = False
    issues_data: bool = False


class Sources(BaseModel):
    github: GitHubSource = Field(default_factory=GitHubSource)
    github_platform: GitHubPlatformSource = Field(default_factory=GitHubPlatformSource)


class Storage(BaseModel):
    warehouse_path: str
    repo_clone_root: str
    curation_dir: str


class Dashboard(BaseModel):
    theme: str = "default"
    output_path: str = "~/data/code-diligence/dashboard/"


class Heuristics(BaseModel):
    abandoned_threshold_days: int = 180
    bus_factor_coverage_pct: int = 50
    fte_inference: bool = True
    fte_inference_signals: list[str] = Field(
        default_factory=lambda: ["email_domain", "commit_cadence", "tenure", "repo_breadth"]
    )
    allow_working_pattern_card: bool = False


class TargetSettings(BaseModel):
    target_id: str
    target_name: str
    description: str | None = None
    sources: Sources = Field(default_factory=Sources)
    storage: Storage
    dashboard: Dashboard = Field(default_factory=Dashboard)
    heuristics: Heuristics = Field(default_factory=Heuristics)

    @model_validator(mode="after")
    def _validate_target_id(self) -> Self:
        if not _TARGET_ID_RE.match(self.target_id):
            raise ValueError(
                f"target_id must be kebab-case (lowercase alphanumerics + hyphens, "
                f"starting and ending with alphanumeric); got: {self.target_id!r}"
            )
        return self
