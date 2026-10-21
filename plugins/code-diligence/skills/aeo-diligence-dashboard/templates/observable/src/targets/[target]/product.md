# Product

```js
import {reportTable} from "../../data/tables.js";
import {query, narrative, axisConfidence} from "../../data/warehouse.js";
import {abandonedRepos, codeAge, codeHealth, couplings, findingsBySeverity, hotspots, securityPeriods} from "../../data/metrics.js";
import {confidenceLine, count, day, pct, targetName, wrap} from "../../data/labels.js";
import {securityChart} from "../../data/charts.js";
import * as Plot from "npm:@observablehq/plot";
const target_id = observable.params.target;
const conf = await axisConfidence(target_id, "product");
const name = await targetName(target_id);
```

<p class="subtitle">${name} · ${confidenceLine(conf)}</p>

## Security findings

<p class="finding">${narr_security.body}</p>

```js
const security = await securityPeriods(target_id);
const narr_security = await narrative(target_id, "product", "security_findings");
display(securityChart(security, {width: Math.min(width, 1040), height: 480, invalidation}));
```

---

## File change hotspots

<p class="finding">${narr.body}</p>

```js
const hotspot_rows = await hotspots(target_id);
const narr = await narrative(target_id, "product", "hotspot_map");
display(reportTable(hotspot_rows, {
  select: false,
  columns: ["path", "repo", "revisions"],
  header: {path: "File", repo: "Repository", revisions: "Changes"},
  format: {path: wrap, repo: wrap, revisions: count},
  width: {path: "55%"},
}));
```

<p class="caption"><span class="source">Source: code-maat.</span> Most-changed files that exist today in production and tooling repositories, top 25.</p>

---

## Code health

<p class="finding">${narr_health.body}</p>

```js
const health = await codeHealth(target_id);
const severity = await findingsBySeverity(target_id);
const narr_health = await narrative(target_id, "product", "code_health");
const score = value => typeof value === "number" ? value.toFixed(1) : value;
const health_tables = html`<div class="code-health-tables">`;
if (health.length) health_tables.append(reportTable(health, {
  select: false,
  columns: ["repo", "average_health", "hotspot_health", "maintainability_average", "performance_average", "file_count"],
  header: {repo: "Repository", average_health: "Health", hotspot_health: "Hotspot health", maintainability_average: "Maintainability", performance_average: "Performance", file_count: "Files scored"},
  format: {repo: wrap, average_health: score, hotspot_health: score, maintainability_average: score, performance_average: score, file_count: count},
  width: {repo: "28%", average_health: "9%", hotspot_health: "14%", maintainability_average: "19%", performance_average: "16%", file_count: "14%"},
}));
else health_tables.append(html`<p>Repowise results were not collected for this target.</p>`);
if (health.length) health_tables.append(html`<section>
<h3>Lowest-scoring files</h3>
${reportTable(health, {
  select: false,
  columns: ["repo", "worst_path", "worst_score"],
  header: {repo: "Repository", worst_path: "File", worst_score: "Score"},
  format: {repo: wrap, worst_path: wrap, worst_score: score},
  width: {repo: "28%", worst_path: "62%", worst_score: "10%"},
})}</section>`);
if (severity.length) health_tables.append(html`<section>
<h3>Code-quality findings by Repowise rating</h3>
${reportTable(severity, {
  select: false,
  header: {repo: "Repository", critical: "Critical", high: "High", medium: "Medium", low: "Low", dead_code: "Dead code"},
  format: {repo: wrap, critical: count, high: count, medium: count, low: count, dead_code: count},
  width: {repo: "28%", critical: "14.4%", high: "14.4%", medium: "14.4%", low: "14.4%", dead_code: "14.4%"},
})}</section>`);
display(health_tables);
```

<p class="caption"><span class="source">Source: Repowise.</span> Scores run from 1 to 10, and higher is healthier. Hotspot health scores the most-changed files. Findings are code-quality markers, such as complex or long methods, counted by Repowise's own rating. They are not security findings. Dead code counts unused exports and unreachable files.</p>

---

## Hidden coupling matrix

<p class="finding">${narr2.body}</p>

```js
const coupling_rows = await couplings(target_id);
const narr2 = await narrative(target_id, "product", "hidden_coupling_matrix");
if (coupling_rows.length) display(reportTable(coupling_rows, {
  select: false,
  columns: ["file_a", "file_b", "repo", "co_change_count", "support_pct", "lift"],
  header: {file_a: "File", file_b: "Changes with", repo: "Repository", co_change_count: "Shared commits", support_pct: "Share of commits", lift: "Lift"},
  format: {file_a: wrap, file_b: wrap, co_change_count: count, support_pct: pct, lift: value => value.toFixed(1)},
}));
```

<p class="caption"><span class="source">Source: code-maat.</span> File pairs that change together more often than chance: lift above 1.5, in more than 5% of the repository's commits.</p>

---

## Code aging chart

<p class="finding">${narr3.body}</p>

```js
const ages = await codeAge(target_id);
const narr3 = await narrative(target_id, "product", "code_aging_chart");
if (ages.length) display(Plot.plot({
  width: Math.min(width, 1040),
  style: {fontSize: "12px"},
  marks: [
    Plot.barY(ages, {x: row => String(row.year), y: "surviving_loc", fill: "repo", tip: true}),
    Plot.ruleY([0]),
  ],
  color: {legend: true, scheme: "observable10"},
  x: {type: "band", label: "Year written"},
  y: {label: "Surviving lines of source code", grid: true},
  marginLeft: 80,
  height: 280,
}));
```

<p class="caption"><span class="source">Source: git-of-theseus.</span> Lines of code that survive today, by the year they were written. JSON, YAML, Markdown and text files are not counted.</p>

---

## Burndown over time

<p class="finding">${narr4.body}</p>

```js
const burndown = await query(`
  SELECT r.repo_id, r.name AS repo, snapshot_at, vintage_year, SUM(surviving_loc) AS surviving_loc
  FROM burndown_series bs JOIN repos r USING (repo_id)
  WHERE r.target_id = ? GROUP BY r.repo_id, r.name, snapshot_at, vintage_year
  ORDER BY r.name, snapshot_at, vintage_year
`, [target_id]);
const narr4 = await narrative(target_id, "product", "burndown_over_time");
const vintages = Array.from(new Set(burndown.map(row => String(row.vintage_year)))).sort();
for (const repo of new Set(burndown.map(row => row.repo))) {
  display(html`<h3>${repo}</h3>`);
  display(Plot.plot({
    width: Math.min(width, 1040),
    style: {fontSize: "12px"},
    marks: [
      Plot.areaY(burndown.filter(row => row.repo === repo), {x: row => new Date(row.snapshot_at), y: "surviving_loc", fill: row => String(row.vintage_year), tip: true}),
      Plot.ruleY([0]),
    ],
    color: {type: "ordinal", domain: vintages, scheme: "observable10", legend: true, label: "Year written"},
    x: {label: null},
    y: {label: "Surviving lines", grid: true},
    marginLeft: 80,
    height: 200,
  }));
}
```

<p class="caption"><span class="source">Source: Hercules.</span> Surviving lines of every tracked file over time, by the year they were written. Each repository has its own sample dates.</p>

---

## Abandoned area register

<p class="finding">${narr5.body}</p>

```js
const abandoned = await abandonedRepos(target_id);
const narr5 = await narrative(target_id, "product", "abandoned_area_register");
if (abandoned.length) display(reportTable(abandoned, {
  select: false,
  columns: ["repo", "last_commit_at", "last_author", "last_msg"],
  header: {repo: "Repository", last_commit_at: "Last commit", last_author: "Last author", last_msg: "Last change"},
  format: {last_commit_at: day, last_msg: wrap},
}));
```

<p class="caption"><span class="source">Source: git history and repository labels.</span> Repositories labeled abandoned, with their last commit.</p>

---

## Language inventory

<p class="finding">${narr6.body}</p>

```js
const stacks = await query(`
  SELECT r.name AS repo, r.language_primary, r.languages
  FROM repos r WHERE r.target_id = ? ORDER BY r.name
`, [target_id]);
const narr6 = await narrative(target_id, "product", "tech_stack_drift");
display(reportTable(stacks, {
  select: false,
  columns: stacks.some(row => row.languages) ? ["repo", "language_primary", "languages"] : ["repo", "language_primary"],
  header: {repo: "Repository", language_primary: "Primary language", languages: "Languages"},
}));
```

<p class="caption"><span class="source">Source: GitHub repository records.</span> Primary language of each repository. Language history is not collected.</p>
