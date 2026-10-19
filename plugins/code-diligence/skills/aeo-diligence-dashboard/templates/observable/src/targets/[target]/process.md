# Process

```js
import {query, narrative, axisConfidence} from "../../data/warehouse.js";
import {ciHealth, delivery, issueTriage} from "../../data/metrics.js";
import {confidenceLine, count, duration, hours, pct, targetName, wrap} from "../../data/labels.js";
import * as Plot from "npm:@observablehq/plot";
const target_id = observable.params.target;
const conf = await axisConfidence(target_id, "process");
const name = await targetName(target_id);
const config = await FileAttachment("../../data/config.json").json();
const allow_working_pattern_card = !!config.allow_working_pattern_card;
```

<p class="subtitle">${name} · ${confidenceLine(conf)}</p>

## Delivery indicators

<p class="finding">${narr.body}</p>

```js
const dora = await delivery(target_id);
const narr = await narrative(target_id, "process", "dora_quadrant");
const uses_releases = dora.some(row => row.releases_total > 0);
display(Inputs.table(dora.map(row => ({
  ...row,
  avg_pr_cycle_time_h: row.avg_pr_cycle_time_h === null ? "No merged PRs" : hours(row.avg_pr_cycle_time_h),
  workflow_failure_rate: row.workflow_failure_rate === null ? "No runs" : pct(row.workflow_failure_rate),
})), {
  columns: uses_releases
    ? ["repo", "releases_l30d", "avg_pr_cycle_time_h", "workflow_failure_rate"]
    : ["repo", "avg_pr_cycle_time_h", "workflow_failure_rate"],
  header: {repo: "Repository", releases_l30d: "GitHub releases, last 30 days", avg_pr_cycle_time_h: "Average PR open to merge", workflow_failure_rate: "Workflow runs not passing"},
}));
```

<p class="caption">From GitHub pull requests${uses_releases ? ", workflow runs and releases" : " and workflow runs"}. Production deployments and incidents are not collected, so these are not DORA metrics.</p>

---

## CI health

<p class="finding">${narr2.body}</p>

```js
const ci = await ciHealth(target_id);
const narr2 = await narrative(target_id, "process", "ci_health");
display(Inputs.table(ci, {
  columns: ["workflow_name", "repo", "runs", "success_rate", "avg_duration_s"],
  header: {workflow_name: "Workflow", repo: "Repository", runs: "Runs", success_rate: "Passing", avg_duration_s: "Average duration"},
  format: {workflow_name: wrap, repo: wrap, runs: count, success_rate: pct, avg_duration_s: duration},
  width: {workflow_name: "36%"},
}));
```

<p class="caption">Completed GitHub Actions runs by workflow file. Cancelled runs count as not passing.</p>

---

## Issue triage health

<p class="finding">${narr3.body}</p>

```js
const issues = await issueTriage(target_id);
const narr3 = await narrative(target_id, "process", "issue_triage_health");
if (issues.length) display(Inputs.table(issues.map(row => ({
  ...row,
  avg_first_response_days: row.avg_first_response_days === null ? "No comments" : row.avg_first_response_days < 1 ? `${Math.round(row.avg_first_response_days * 24 * 60)} min` : `${row.avg_first_response_days.toFixed(1)} days`,
})), {
  header: {repo: "Repository", total_issues: "Issues", avg_first_response_days: "Average time to first comment", stale_open: "Open over 90 days"},
  format: {total_issues: count, stale_open: count},
}));
```

<p class="caption">GitHub Issues only. Issues tracked in other tools do not appear.</p>

```js
if (allow_working_pattern_card) {
  const patterns = await query(`
    SELECT r.name AS repo,
           EXTRACT(DOW FROM cf.author_date) AS dow,
           EXTRACT(HOUR FROM cf.author_date) AS hour,
           COUNT(*) AS commits
    FROM commits_fact cf JOIN repos r ON r.repo_id = cf.repo_id
    WHERE r.target_id = ?
    GROUP BY r.repo_id, r.name, dow, hour
  `, [target_id]);
  const narr5 = await narrative(target_id, "process", "working_pattern_signals");
  display(html`<hr><h2>Working pattern signals</h2><p class="finding">${narr5.body}</p>`);
  display(Plot.plot({
    marks: [Plot.cell(patterns, {x: "hour", y: "dow", fill: "commits", inset: 0.5, tip: true})],
    facet: {data: patterns, x: "repo", marginTop: 30},
    x: {label: "Hour (UTC)"},
    y: {label: "Day (UTC)", tickFormat: day => ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][day]},
    height: 200, color: {scheme: "blues"},
  }));
}
```
