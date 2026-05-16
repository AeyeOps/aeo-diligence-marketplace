"""Canonical taxonomy of narrative sections per axis. Mirrors spec §6."""
from dataclasses import dataclass
from typing import Iterable

import duckdb


@dataclass(frozen=True)
class SectionDef:
    axis: str
    section_key: str
    title: str
    description: str


TAXONOMY: tuple[SectionDef, ...] = (
    # People
    SectionDef("people", "bus_factor_map", "Bus factor map",
               "Repos colored by min-N FTE authors needed to cover 50% of code knowledge."),
    SectionDef("people", "knowledge_concentration", "Knowledge concentration heatmap",
               "% of code owned by top-1/3/5 FTEs per repo; >60% top-1 = key-person risk."),
    SectionDef("people", "contributor_activity_timeline", "Contributor activity timeline",
               "Monthly active contributors stacked by class, with joiner/leaver overlays."),
    SectionDef("people", "communication_graph", "Communication graph",
               "Force-directed graph of co-editing relationships."),
    SectionDef("people", "hero_dependency_register", "Hero/dependency register",
               "Files where one person owns 90%+ of recent commits."),
    # Product
    SectionDef("product", "hotspot_map", "Hotspot map",
               "Repo treemap; size=LOC, color=revisions × complexity."),
    SectionDef("product", "hidden_coupling_matrix", "Hidden coupling matrix",
               "Heatmap of file/module pairs with high co-change support × lift."),
    SectionDef("product", "code_aging_chart", "Code aging chart",
               "git-of-theseus stacked area: how much code from each cohort year still survives."),
    SectionDef("product", "burndown_over_time", "Burndown over time",
               "hercules per-repo time-series of code survival, comparable across repos."),
    SectionDef("product", "abandoned_area_register", "Abandoned area register",
               "Modules with no commits in N days (default 180), with last-author + last-message."),
    SectionDef("product", "tech_stack_drift", "Tech-stack inventory + drift",
               "Per-repo language and dependency footprint with introduced/deprecated bands."),
    # Process
    SectionDef("process", "dora_quadrant", "DORA quadrant",
               "Deploy frequency, lead time, change failure rate, MTTR per repo."),
    SectionDef("process", "review_discipline", "Review discipline",
               "Review latency, reviewers per PR, self-merge rate, merge-without-review rate."),
    SectionDef("process", "ci_health", "CI health",
               "Workflow success rate over time, flaky-test inference, slowest jobs."),
    SectionDef("process", "issue_triage_health", "Issue triage health",
               "Open/closed over time, time-to-first-response, stale count."),
    SectionDef("process", "working_pattern_signals", "Working pattern signals",
               "Commits by hour-of-day × day-of-week, aggregated to repo level."),
)


def load_taxonomy_into_warehouse(conn: duckdb.DuckDBPyConnection) -> None:
    """Idempotent upsert of TAXONOMY into axes_taxonomy."""
    conn.execute("DELETE FROM axes_taxonomy")
    rows = [(s.axis, s.section_key, s.title, s.description) for s in TAXONOMY]
    conn.executemany(
        "INSERT INTO axes_taxonomy (axis, section_key, title, description) VALUES (?, ?, ?, ?)",
        rows,
    )


def sections_for_axis(axis: str) -> Iterable[SectionDef]:
    return (s for s in TAXONOMY if s.axis == axis)
