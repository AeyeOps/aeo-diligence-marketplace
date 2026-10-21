# Security chart

The overview and Product page use the same ECharts component and prepared data. Its stable narrative key is `product/security_findings`. The chart shows additions above zero, removals below zero, and backlog as a line. Use **Opened / Closed** for event data and **Added / Removed** for snapshot or aggregate data. A removal from snapshots does not establish that someone patched a vulnerability. Describe the population from the prepared `scope`, which comes from recorded collection selections or supplied chart input. Mixed inputs do not imply a particular period or combination of sources.

## Choose the period and evidence

Use the user's requested range and interval. Otherwise use monthly periods across the recorded history. Never substitute the six-month `security_monthly` cache for a longer or differently grouped request. Prepare the chart before writing its narrative:

```sh
"$PLUGIN_ROOT/bin/run" python -m code_diligence.security.chart \
  --warehouse "$WAREHOUSE_PATH" --target-id "$TARGET_ID" \
  --output "$TARGET_FOLDER/security-prepared.json"
```

To change the interval or supply external counts, save a chart input JSON file, record its path as `dashboard.security_chart_path` in the target settings, and pass it to both preparation and rendering with `--security-chart "$SECURITY_CHART_PATH"`. Resolve a relative setting against the folder containing `diligence.local.md`. The CLI itself resolves relative paths against its working directory. Preparation migrates a temporary warehouse copy without changing the source assessment or collecting live data. The prepared file contains one chart per target ID.

For example, this input reads the native saved observations and groups them into calendar quarters:

```json
{
  "target_id": "example-target",
  "interval": "quarter",
  "range_start": "2026-01-01",
  "range_end": "2027-01-01",
  "timezone": "America/New_York"
}
```

## Input attributes

| Attribute | Meaning |
|---|---|
| `target_id` | Required warehouse target. |
| `interval` | `day`, `week`, `month` (default), `quarter`, `year`, or `custom`. |
| `range_start`, `range_end` | Optional display bounds, start inclusive and end exclusive. Boundary periods are clipped. |
| `timezone` | IANA timezone. Native data uses its configured month timezone; supplied rows default to UTC. Naive dates and times use this timezone. |
| `week_start` | Monday = 0 through Sunday = 6; default 0. |
| `fiscal_year_start_month` | January = 1 through December = 12; default 1. Applies to quarters and years. |
| `periods` | For `custom`, explicit non-overlapping `{ "start": "...", "end": "..." }` intervals. Gaps remain gaps. |
| `as_of` | Latest evidence time to use. Native observations stop at the latest saved read; an explicit baseline or anchor can add a known point outside that history. Supplied measures and points observed after `as_of` are omitted. |
| `source`, `scope` | Required for supplied rows: evidence producer and included population. Native inputs derive these from Inspector reads. |
| `counting_basis` | Required for supplied rows: `events`, `snapshots`, `distinct_findings`, `provider_aggregate`, or `mixed`. For mixed inputs, describe the periods and populations in `scope`. |
| `severities` | Optional complete list of severity categories in scope. Native inputs derive it from covered severities; supplied inputs derive it from their rows. Use explicit categories when some are entirely missing. An empty list supports total-only data. |
| `rows` | Omit to read native observations. Supply an array for external counts; `[]` means no supplied observations. See below. |
| `baseline` | Optional `{ "at": "...", "value": 0, "description": "..." }` starting point. Zero requires evidence; lack of earlier observations is not a zero baseline. |
| `backlog_anchor` | Optional independently known backlog at a timestamp, with the same shape as `baseline`. It can support backward calculation. |
| `backlog_estimates` | Optional array of `{ "at": "...", "value": 0, "description": "..." }` points already calculated by the source. Preserve their explanation and any known mismatch. The chart shows them as estimates; observed backlog takes precedence. |

Each supplied row has required `period_start` and `period_end`, and optional `severity`. Omit `severity` for a total across the population. Counts are optional nonnegative integers: `added`, `removed`, `opening_backlog`, `closing_backlog`. Optional `adjustment` is signed. Omission or null means unknown; zero means measured zero. Do not create counts to fill an incomplete chart.

`coverage` optionally maps each measure to `{ "start": "...", "end": "...", "status": "complete|partial|unknown" }`. Default status is unknown. For movements, timestamps describe the measurement interval. For backlog, they identify the observation time. Mark a movement complete only if it covers the whole period being calculated; mark a stock complete only at its stated boundary. `opening_from_first_read: true` identifies an opening observed inside the period rather than at its start.

## What can be drawn

| Available evidence | Result |
|---|---|
| Additions only or removals only | That bar series, with the other side missing. |
| Opening or closing backlog only | The known backlog points, with their observation dates and breaks where the total is unknown. Closing points take precedence; an opening point is shown when there is no observed or calculated closing point. |
| Some severity counts | Their stacks; partial totals carry an asterisk. Missing categories do not become zero. |
| Total counts without severity | A single Total stack or backlog line. |
| Baseline only or anchor only | The known point, with its actual date and description. |
| Supplied backlog estimates | The supplied curve with hollow markers and its explanation in the tooltip. |
| Complete movements plus a known stock | Forward or backward backlog calculation across contiguous, fully covered periods. |
| No observations in a requested period | “No data,” not zero. |

Backlog calculation uses `closing = opening + added - removed + adjustment`. All three movements must be known and completely covered; use an explicit zero adjustment only when the source supports it. An unknown movement, coverage gap, or unmatched boundary stops calculation. `provider_aggregate` and `mixed` counts are displayed but are not assumed to satisfy that identity. Existing source estimates can be carried in `backlog_estimates` without recalculating them. Explicit stocks take precedence over calculated points; a supplied balance mismatch is disclosed in the tooltip. A stock total requires all in-scope severities measured at the same time or an explicit total.

## Regrouping

Native rows are recomputed from raw `security_reads` and `security_observations` for each requested period. Opening is the last covered read before the period, or its first covered read when no prior read exists. Added is the distinct set seen during the period but absent from opening. Removed is the union of opening and seen sets absent from the last read. Closing is the last read's set. Only a read covering a severity can establish zero for it. Read times and partial coverage remain attached to each measure.

Supplied event counts can be summed into coarser periods. Opening and closing stocks use the first and last applicable observation, never their sum. Distinct-finding counts, snapshot differences, and unspecified provider aggregates cannot safely be summed into a new period without identities or raw observations, so their movements are omitted when regrouping. Coarse totals cannot be split into finer periods or prorated across clipped boundaries. Supply raw native observations or already grouped counts when such a conversion is needed.

## Narration and review

Pass the prepared target document as `metric_context` for `product/security_findings`, alongside this reference. Describe the displayed interval, scope, latest backlog and available movements. Distinguish events from snapshot changes, observed points from calculated points, and missing history from zero. Keep coverage detail in the tooltip; do not turn the chart into an implementation report.

In tooltips, group measures that share coverage dates and identify severity subsets with different coverage. Use one date for a point observation.

Activate the test tab and wait for the chart itself to render. Document readiness alone does not prove that Observable has evaluated its visible cells.

Review the actual overview and Product chart with the same input. For chart changes, exercise a real populated period, a requested empty period, a partial input, a zero total, legend toggles and tooltips. Check that labels remain legible and clear of the bars when a visible bar total is close to backlog, including after hiding a large severity category. Check the first period for overlap between its starting point, month label and vertical-axis captions. Totals must follow visible stacks, and the security link must reach Product. Check existing narrative wording when the displayed measure changes; a preserved paragraph about all findings open during a period does not explain a new additions/removals chart. Follow the active harness's browser-testing instructions. Fix observed failures and rerun the affected journey before declaring completion.
