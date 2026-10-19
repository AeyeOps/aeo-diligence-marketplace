# Process axis — 4 cards

| section_key | Evidence and interpretation |
|---|---|
| `dora_quadrant` | Repository delivery indicators: GitHub releases in the last 30 days, average PR cycle time, and workflow failure fraction. These are not DORA metrics: production deployment and incident data are absent. |
| `ci_health` | Completed workflow outcomes and durations by repository and workflow file. |
| `issue_triage_health` | Average time to first issue comment and count of issues still open after 90 days. |
| `working_pattern_signals` | Repository-level commit day/hour distribution, only when `heuristics.allow_working_pattern_card` is true. |

PRs, workflows, releases, and issues require a full run, `sources.github.token_env`, and their configured data switches. Working patterns use walker facts. Empty platform tables may mean collection was disabled, failed, or returned no records; inspect settings and Health before interpreting them. These cards see only work recorded in GitHub: review done before a commit, releases shipped another way and issues tracked elsewhere do not appear, so an empty result means not recorded in GitHub, not that the work did not happen.

Narrate observed rates with their population and time span. Do not compare release counts or PR cycle time with DORA deployment thresholds. A first comment is not necessarily a maintainer response. Repository evidence alone does not establish employee performance or business risk acceptance.

The working-pattern setting defaults to false. When enabled, describe aggregate repository patterns without identifying individuals or inferring burnout. See [the privacy contract](../../aeo-diligence-dashboard/references/privacy-gate.md).
