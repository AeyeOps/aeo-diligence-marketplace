# Product

```js
import {query, narrative, axisConfidence} from "../../data/warehouse.js";
import {confidenceLine, count, day, pct, targetName, wrap} from "../../data/labels.js";
import * as Plot from "npm:@observablehq/plot";
const target_id = observable.params.target;
const conf = await axisConfidence(target_id, "product");
const name = await targetName(target_id);
```

<p class="subtitle">${name} · ${confidenceLine(conf)}</p>

## File change hotspots

<p class="finding">${narr.body}</p>

```js
const hotspots = await query(`
  SELECT r.name AS repo, fm.path, fm.revisions
  FROM file_metrics fm
  JOIN repos r ON r.repo_id = fm.repo_id
  JOIN repo_classification rc ON rc.repo_id = fm.repo_id
  WHERE r.target_id = ? AND rc.class IN ('production', 'tooling')
  ORDER BY fm.revisions DESC, fm.path LIMIT 25
`, [target_id]);
const narr = await narrative(target_id, "product", "hotspot_map");
display(Inputs.table(hotspots, {
  columns: ["path", "repo", "revisions"],
  header: {path: "File", repo: "Repository", revisions: "Changes"},
  format: {path: wrap, revisions: count},
  width: {path: "55%"},
}));
```

<p class="caption">Most-changed files in production and tooling repositories, top 25.</p>

---

## Hidden coupling matrix

<p class="finding">${narr2.body}</p>

```js
const couplings = await query(`
  SELECT r.name AS repo, cp.file_a, cp.file_b, cp.co_change_count, cp.support_pct, cp.lift
  FROM coupling_pairs cp
  JOIN repos r ON r.repo_id = cp.repo_id
  WHERE r.target_id = ? AND cp.lift > 1.5 AND cp.support_pct > 0.05
  ORDER BY cp.lift DESC LIMIT 100
`, [target_id]);
const narr2 = await narrative(target_id, "product", "hidden_coupling_matrix");
if (couplings.length) display(Inputs.table(couplings, {
  columns: ["file_a", "file_b", "repo", "co_change_count", "support_pct", "lift"],
  header: {file_a: "File", file_b: "Changes with", repo: "Repository", co_change_count: "Shared commits", support_pct: "Share of commits", lift: "Lift"},
  format: {file_a: wrap, file_b: wrap, co_change_count: count, support_pct: pct, lift: value => value.toFixed(1)},
}));
```

<p class="caption">File pairs that change together far more often than chance: lift above 1.5, in more than 5% of the repository's commits.</p>

---

## Code aging chart

<p class="finding">${narr3.body}</p>

```js
const ages = await query(`
  SELECT r.name AS repo, cab.bucket_start_year AS year, SUM(cab.surviving_loc) AS surviving_loc
  FROM code_age_buckets cab
  JOIN repos r ON r.repo_id = cab.repo_id
  WHERE r.target_id = ?
  GROUP BY 1, 2 ORDER BY 2, 1
`, [target_id]);
const narr3 = await narrative(target_id, "product", "code_aging_chart");
if (ages.length) display(Plot.plot({
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

<p class="caption">Lines of source code that survive today, by the year they were written (git-of-theseus). JSON, Markdown and other data files are not counted.</p>

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

<p class="caption">Surviving lines of every tracked file over time, by the year they were written (hercules). Each repository has its own sample dates.</p>

---

## Abandoned area register

<p class="finding">${narr5.body}</p>

```js
const abandoned = await query(`
  SELECT r.name AS repo, r.last_commit_at, r.is_archived,
         (SELECT cf.author_email FROM commits_fact cf WHERE cf.repo_id = r.repo_id ORDER BY cf.author_date DESC LIMIT 1) AS last_author,
         (SELECT cf.message_first_line FROM commits_fact cf WHERE cf.repo_id = r.repo_id ORDER BY cf.author_date DESC LIMIT 1) AS last_msg
  FROM repos r JOIN repo_classification rc ON rc.repo_id = r.repo_id
  WHERE r.target_id = ? AND rc.class = 'abandoned'
  ORDER BY r.last_commit_at ASC
`, [target_id]);
const narr5 = await narrative(target_id, "product", "abandoned_area_register");
if (abandoned.length) display(Inputs.table(abandoned, {
  columns: ["repo", "last_commit_at", "last_author", "last_msg"],
  header: {repo: "Repository", last_commit_at: "Last commit", last_author: "Last author", last_msg: "Last change"},
  format: {last_commit_at: day, last_msg: wrap},
}));
```

---

## Language inventory

<p class="finding">${narr6.body}</p>

```js
const stacks = await query(`
  SELECT r.name AS repo, r.language_primary, r.languages
  FROM repos r WHERE r.target_id = ? ORDER BY r.name
`, [target_id]);
const narr6 = await narrative(target_id, "product", "tech_stack_drift");
display(Inputs.table(stacks, {
  columns: stacks.some(row => row.languages) ? ["repo", "language_primary", "languages"] : ["repo", "language_primary"],
  header: {repo: "Repository", language_primary: "Primary language", languages: "Languages"},
}));
```

<p class="caption">Primary language from each repository's GitHub record. Language history is not collected.</p>
