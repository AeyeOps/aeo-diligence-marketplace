"""Canonical dashboard sections and the evidence collected for each."""
from collections.abc import Iterable
from dataclasses import dataclass

import duckdb


@dataclass(frozen=True)
class SectionDef:
    axis: str
    section_key: str
    title: str
    description: str


TAXONOMY: tuple[SectionDef, ...] = (
    SectionDef("people", "bus_factor_map", "Bus factor map",
               "Minimum confirmed FTEs covering 50% of non-bot git-fame LOC in production or tooling repositories, after combining identity aliases. Insufficient FTE ownership is unavailable."),
    SectionDef("people", "knowledge_concentration", "Knowledge concentration",
               "Top canonical contributor's share of git-fame LOC per repository."),
    SectionDef("people", "contributor_activity_timeline", "Contributor activity timeline",
               "Monthly distinct canonical contributors grouped by confirmed classification; unclassified contributors remain unknown."),
    SectionDef("people", "communication_graph", "Communication graph",
               "Canonical authors linked when they change the same file in the same month. Edge weights count shared file/month combinations, not observed communication."),
    SectionDef("people", "hero_dependency_register", "Hero / dependency register",
               "Files where one author accounts for at least 90% of historical additions according to code-maat."),
    SectionDef("product", "hotspot_map", "File change hotspots",
               "Files that exist at HEAD in production or tooling repositories, ranked by revision count. Complexity is not collected or included in this ranking."),
    SectionDef("product", "code_health", "Code health",
               "Repowise health scores from 1 to 10, higher is healthier, and Repowise findings by severity per repository."),
    SectionDef("product", "security_findings", "Security findings",
               "Findings added, removed and remaining on in-scope resources over the requested periods. "
               "Counting basis and coverage distinguish observed events, snapshot changes and provider aggregates."),
    SectionDef("product", "hidden_coupling_matrix", "Hidden coupling matrix",
               "Code-maat file pairs with shared-commit counts, support and lift from walker facts. The card displays lift above 1.5 and support above 0.05."),
    SectionDef("product", "code_aging_chart", "Code aging chart",
               "Current surviving LOC by introduction year from git-of-theseus."),
    SectionDef("product", "burndown_over_time", "Burndown over time",
               "Surviving LOC at each snapshot, grouped by vintage year, from hercules."),
    SectionDef("product", "abandoned_area_register", "Abandoned area register",
               "Repositories with confirmed abandoned classification and their last commit evidence."),
    SectionDef("product", "tech_stack_drift", "Language inventory",
               "Current GitHub primary language per repository. Historical technology changes and language LOC totals are not collected."),
    SectionDef("process", "dora_quadrant", "Delivery indicators",
               "GitHub releases in the last 30 days, average PR cycle time and workflow failure fraction. These are not DORA deployment or incident metrics."),
    SectionDef("process", "ci_health", "CI health",
               "Completed workflow outcomes and durations by repository and workflow file."),
    SectionDef("process", "issue_triage_health", "Issue triage health",
               "Average time to first issue comment and count of issues still open after 90 days. A first comment is not necessarily a maintainer response."),
    SectionDef("process", "working_pattern_signals", "Working pattern signals",
               "Commits by hour-of-day × day-of-week, aggregated to repo level."),
)


def load_taxonomy_into_warehouse(conn: duckdb.DuckDBPyConnection) -> None:
    """Idempotent upsert of TAXONOMY into axes_taxonomy."""
    conn.execute("UPDATE narratives SET axis = 'product' WHERE axis = 'process' AND section_key = 'security_findings'")
    conn.execute("DELETE FROM axes_taxonomy")
    rows = [(s.axis, s.section_key, s.title, s.description) for s in TAXONOMY]
    conn.executemany(
        "INSERT INTO axes_taxonomy (axis, section_key, title, description) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.execute(
        "DELETE FROM narratives WHERE (axis, section_key) NOT IN (SELECT axis, section_key FROM axes_taxonomy)"
    )


def sections_for_axis(axis: str) -> Iterable[SectionDef]:
    return (s for s in TAXONOMY if s.axis == axis)
