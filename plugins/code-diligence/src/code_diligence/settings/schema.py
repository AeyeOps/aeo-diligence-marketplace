"""Pydantic models for per-target settings."""
import re
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

_TARGET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


class GitHubSource(BaseModel):
    enabled: bool = False
    token_env: str | None = None
    orgs: list[str] = Field(default_factory=list)
    include_archived: bool = False

    @model_validator(mode="after")
    def _require_orgs_when_enabled(self) -> Self:
        if self.enabled and not self.orgs:
            raise ValueError("github.orgs is required (non-empty) when github.enabled is true")
        return self


class GitHubPlatformSource(BaseModel):
    pr_data: bool = False
    actions_data: bool = False
    issues_data: bool = False

    @property
    def requested(self) -> bool:
        return self.pr_data or self.actions_data or self.issues_data


class AwsInspectorSource(BaseModel):
    enabled: bool = False
    profile: str | None = None
    region: str | None = None
    resource_prefixes: list[str] = Field(default_factory=list)
    fix_available: list[Literal["YES", "NO", "PARTIAL"]] = Field(default_factory=list)
    snapshot_dirs: list[str] = Field(default_factory=list)
    timezone: str = "UTC"

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"aws_inspector.timezone is not a known time zone: {value}") from exc
        return value

    @model_validator(mode="after")
    def _require_profile_and_region_when_enabled(self) -> Self:
        if self.enabled and not (self.profile and self.region):
            raise ValueError("aws_inspector.profile and aws_inspector.region are required when aws_inspector.enabled is true")
        return self


class Sources(BaseModel):
    github: GitHubSource = Field(default_factory=GitHubSource)
    github_platform: GitHubPlatformSource = Field(default_factory=GitHubPlatformSource)
    aws_inspector: AwsInspectorSource = Field(default_factory=AwsInspectorSource)

    @model_validator(mode="after")
    def _require_token_for_github_api(self) -> Self:
        if (self.github.enabled or self.github_platform.requested) and not self.github.token_env:
            raise ValueError(
                "github.token_env is required when github.enabled or a github_platform switch is true"
            )
        return self


class Storage(BaseModel):
    warehouse_path: str
    repo_clone_root: str
    curation_dir: str


class Dashboard(BaseModel):
    output_path: str = "~/data/code-diligence/dashboard/"
    security_chart_path: str | None = None
    repository_labels: dict[str, str] = Field(default_factory=dict)
    workflow_labels: dict[str, str] = Field(default_factory=dict)
    contributor_labels: dict[str, str] = Field(default_factory=dict)


class Heuristics(BaseModel):
    abandoned_threshold_days: int = 180
    fte_inference: bool = True
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
