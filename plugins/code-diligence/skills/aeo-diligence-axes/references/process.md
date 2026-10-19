# Process axis — 5 cards

| section_key | Evidence and interpretation |
|---|---|
| `dora_quadrant` | Repository delivery indicators: releases in the last 30 days, average PR cycle time, and workflow failure fraction. These are not DORA metrics: production deployment and incident data are absent. |
| `review_discipline` | PR review latency, distinct reviewer count, self-merge fraction among merged PRs with known merger, and merged PRs without approvals. |
| `ci_health` | Completed workflow outcomes and durations by repository and workflow. |
| `issue_triage_health` | Average time to first issue comment and count of issues still open after 90 days. |
| `working_pattern_signals` | Repository-level commit day/hour distribution, only when `heuristics.allow_working_pattern_card` is true. |

PRs, workflows, releases, and issues require a full run, `sources.github.token_env`, and their configured data switches. Working patterns use walker facts. Empty platform tables may mean collection was disabled, failed, or returned no records; inspect settings and Health before interpreting them.

Narrate observed rates with their population and time span. Do not compare release counts or PR cycle time with DORA deployment thresholds. A first comment is not necessarily a maintainer response. Repository evidence alone does not establish review quality, employee performance, or business risk acceptance.

The working-pattern setting defaults to false. When enabled, describe aggregate repository patterns without identifying individuals or inferring burnout. See [the privacy contract](../../aeo-diligence-dashboard/references/privacy-gate.md).
