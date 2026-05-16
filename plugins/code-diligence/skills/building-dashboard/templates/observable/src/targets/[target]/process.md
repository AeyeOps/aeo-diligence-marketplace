# Process — ${observable.params.target}

```js
import { query, narrative, axisConfidence } from "../../data/warehouse.js";
import * as Plot from "npm:@observablehq/plot";
const target_id = observable.params.target;
const conf = await axisConfidence(target_id, "process");
const config = await FileAttachment("../../data/config.json").json();
const allow_working_pattern_card = !!config.allow_working_pattern_card;
```

> Confidence: **${conf.confidence_class}** (${conf.signal_completeness_pct?.toFixed?.(0) ?? 0}% signal complete)

## DORA quadrant

```js
const dora = await query(`
  SELECT r.name AS repo,
         (SELECT COUNT(*) FROM release_metrics rm WHERE rm.repo_id = r.repo_id
           AND rm.released_at >= CURRENT_DATE - INTERVAL '30 days') AS deploys_l30d,
         (SELECT AVG(EXTRACT(EPOCH FROM (pm.merged_at - pm.opened_at))/3600.0)
           FROM pr_metrics pm WHERE pm.repo_id = r.repo_id AND pm.merged_at IS NOT NULL) AS avg_lead_time_h,
         (SELECT 1.0 - AVG(CASE WHEN am.conclusion='success' THEN 1.0 ELSE 0.0 END)
           FROM actions_metrics am WHERE am.repo_id = r.repo_id) AS change_failure_rate,
         NULL AS mttr_h  -- MTTR requires incident data; out of scope for v1
  FROM repos r WHERE r.target_id = ?
`, [target_id]);
const narr = await narrative(target_id, "process", "dora_quadrant");
display(Inputs.table(dora, { columns: ["repo", "deploys_l30d", "avg_lead_time_h", "change_failure_rate"] }));
```

> ${narr.body_md}

---

## Review discipline

```js
const review = await query(`
  SELECT r.name AS repo,
         AVG(pm.review_latency_hours) AS avg_review_latency_h,
         AVG(pm.num_reviewers) AS avg_reviewers,
         AVG(CASE WHEN pm.was_self_merged THEN 1.0 ELSE 0.0 END) AS self_merge_rate,
         AVG(CASE WHEN pm.approvals = 0 AND pm.merged_at IS NOT NULL THEN 1.0 ELSE 0.0 END) AS merge_without_review_rate
  FROM pr_metrics pm JOIN repos r ON r.repo_id = pm.repo_id
  WHERE r.target_id = ? GROUP BY r.repo_id, r.name
`, [target_id]);
const narr2 = await narrative(target_id, "process", "review_discipline");
display(Inputs.table(review));
```

> ${narr2.body_md}

---

## CI health

```js
const ci = await query(`
  SELECT r.name AS repo, am.workflow_name,
         AVG(CASE WHEN am.conclusion='success' THEN 1.0 ELSE 0.0 END) AS success_rate,
         AVG(am.duration_seconds) AS avg_duration_s
  FROM actions_metrics am JOIN repos r ON r.repo_id = am.repo_id
  WHERE r.target_id = ? GROUP BY r.repo_id, r.name, am.workflow_name
  ORDER BY success_rate ASC
`, [target_id]);
const narr3 = await narrative(target_id, "process", "ci_health");
display(Inputs.table(ci));
```

> ${narr3.body_md}

---

## Issue triage health

```js
const issues = await query(`
  SELECT r.name AS repo,
         COUNT(*) AS total_issues,
         AVG(im.days_to_first_response) AS avg_first_response_days,
         SUM(CASE WHEN im.state='open' AND im.opened_at < CURRENT_DATE - INTERVAL '90 days' THEN 1 ELSE 0 END) AS stale_open
  FROM issue_metrics im JOIN repos r ON r.repo_id = im.repo_id
  WHERE r.target_id = ? GROUP BY r.repo_id, r.name
`, [target_id]);
const narr4 = await narrative(target_id, "process", "issue_triage_health");
display(Inputs.table(issues));
```

> ${narr4.body_md}

---

## Working pattern signals (repo-level only)

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
  // Heatmap: facet by repo, x=hour, y=dow, fill=commits
  display(Plot.plot({
    marks: [Plot.cell(patterns, { x: "hour", y: "dow", fill: "commits", inset: 0.5, tip: true })],
    fx: { interval: 0 },
    facet: { data: patterns, x: "repo", marginTop: 30 },
    height: 200, color: { scheme: "blues" },
  }));
  display(html`<blockquote>${narr5.body_md}</blockquote>`);
} else {
  display(html`<p><em>Working pattern signals disabled — set <code>allow_working_pattern_card: true</code> in settings to enable.</em></p>`);
}
```
