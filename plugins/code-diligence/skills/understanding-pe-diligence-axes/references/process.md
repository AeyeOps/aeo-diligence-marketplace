# Process axis — 5 cards

GitHub-platform-dependent. `axis_confidence` is `low` on quick tier (no platform pass); `medium` to `high` on full tier when `sources.github.enabled: true` and the token has the right scopes.

## Card map

| section_key | Card | Backed by | Primary source | Tier |
|---|---|---|---|---|
| `dora_quadrant` | DORA quadrant | `release_metrics` + `actions_metrics` + `pr_metrics` (MTTR is `NULL` — out of scope for v1) | GitHub platform pass | full |
| `review_discipline` | Review discipline | `pr_metrics` (review latency, reviewer count, self-merge rate, merge-without-review rate) | GitHub platform pass | full |
| `ci_health` | CI health | `actions_metrics` (success rate, duration per workflow) | GitHub platform pass | full |
| `issue_triage_health` | Issue triage health | `issue_metrics` (first-response days, stale-open count) | GitHub platform pass | full |
| `working_pattern_signals` | Working pattern signals (repo-level only) | `commits_fact` (DOW × hour aggregation) | walker | quick — **but privacy-gated** |

## Source dependencies

| Source | Without it | Effect on Process confidence |
|---|---|---|
| GitHub platform pass (PR data) | DORA `avg_lead_time_h` and `review_discipline` empty | `low` |
| GitHub platform pass (Actions data) | DORA `change_failure_rate` and `ci_health` empty | `low` to `medium` |
| GitHub platform pass (Releases data) | DORA `deploys_l30d` empty | `low` to `medium` |
| GitHub platform pass (Issues data) | `issue_triage_health` empty | `medium` |
| Walker | `working_pattern_signals` empty (also kills People axis) | `low` |

## The privacy gate on `working_pattern_signals`

Unlike the other four cards, `working_pattern_signals` renders on quick tier (it only needs `commits_fact`), but it is gated behind `heuristics.allow_working_pattern_card` in settings — default `false`. When the flag is off, the card shows an opt-in notice instead of the heatmap.

Why: even though the aggregation is repo-level (no per-person heatmap), commit-time signal is sensitive in some jurisdictions and diligence scopes. See `skills/building-dashboard/references/privacy-gate.md` for the decision matrix.

When narrating this card with the flag on, **never** identify individuals. The narrative should describe the repo-level pattern only ("weekday-business-hours skew" or "Sunday spike on infra-team repos"), not who is committing when.

## Narration patterns per card

- **dora_quadrant** — Lead with the quadrant position vs. the DORA "elite" thresholds (multiple deploys/day, <1h lead time, <15% change-fail, <1h MTTR). Note that MTTR is currently `NULL` — say "MTTR unavailable" rather than skip it.
- **review_discipline** — Lead with the self-merge rate. >25% self-merges in production repos is a finding. Reviewer count >2 average suggests healthy review culture.
- **ci_health** — Lead with the lowest-success-rate workflow in any production repo. <90% success on a workflow that gates merges is a finding.
- **issue_triage_health** — Lead with the median days-to-first-response and the count of issues open >90 days. Both above the diligence target's industry norm is a finding.
- **working_pattern_signals** — Only narrate when the flag is on. Lead with the dominant DOW band. Avoid value-loaded language about "burnout signals" — describe the pattern; let the partner interpret.
