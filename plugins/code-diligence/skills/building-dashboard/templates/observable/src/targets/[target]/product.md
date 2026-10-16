# Product — ${observable.params.target}

```js
import { query, narrative } from "../../data/warehouse.js";
import * as Plot from "npm:@observablehq/plot";
const target_id = observable.params.target;
```

## File change hotspots

Revision counts show change frequency. Complexity is not measured by the git walker. Hover a label or point to read its full repository and file path.

```js
const hotspots = await query(`
  SELECT r.name AS repo, fm.path,
         fm.revisions, fm.complexity_proxy,
         (fm.revisions * COALESCE(fm.complexity_proxy, 1.0)) AS hotspot_score
  FROM file_metrics fm
  JOIN repos r ON r.repo_id = fm.repo_id
  JOIN repo_classification rc ON rc.repo_id = fm.repo_id
  WHERE r.target_id = ? AND rc.class IN ('production', 'tooling')
  ORDER BY hotspot_score DESC LIMIT 200
`, [target_id]);
const narr = await narrative(target_id, "product", "hotspot_map");
```

```js
if (!hotspots.length) {
  display(html`<p>No file-change rows match the current repository classifications. Review <a href="curation.html">Curation</a> and <a href="health.html">Health</a>.</p>`);
} else display(Plot.plot({
  marks: [
    Plot.axisY({label: null, lineWidth: 28, textOverflow: "ellipsis-middle"}),
    Plot.dot(hotspots, {
      x: "revisions", y: d => `${d.repo}/${d.path}`,
      r: d => Math.sqrt(d.hotspot_score),
      fill: d => d.hotspot_score > 100 ? "crimson" : "steelblue",
      stroke: "white", strokeWidth: 0.5,
      title: d => `${d.repo}/${d.path}\nRevisions: ${d.revisions}`,
      tip: true,
    }),
  ],
  x: { label: "Revisions" },
  y: { domain: hotspots.slice(0, 20).map(d => `${d.repo}/${d.path}`) },
  marginLeft: 300,
  height: Math.max(240, 24 * Math.min(20, hotspots.length)),
}));
```

> ${narr.body_md}

---

## Hidden coupling matrix

```js
const couplings = await query(`
  SELECT cp.repo_id, cp.file_a, cp.file_b, cp.support_pct, cp.lift
  FROM coupling_pairs cp
  JOIN repos r ON r.repo_id = cp.repo_id
  WHERE r.target_id = ? AND cp.lift > 1.5 AND cp.support_pct > 0.05
  ORDER BY cp.lift DESC LIMIT 100
`, [target_id]);
const narr2 = await narrative(target_id, "product", "hidden_coupling_matrix");
if (couplings.length) {
  display(html`<p>${couplings.length} pairs match the current filters. Support is the share of repository commits that changed both files.</p>`);
  display(Inputs.table(couplings, {
    columns: ["repo_id", "file_a", "file_b", "support_pct", "lift"],
    header: {repo_id: "Repository", file_a: "File A", file_b: "File B", support_pct: "Support", lift: "Lift"},
    width: {repo_id: 160, file_a: 200, file_b: 200, support_pct: 75, lift: 60},
    format: {
      repo_id: value => html`<span style="white-space:normal;overflow-wrap:anywhere;">${value}</span>`,
      file_a: value => html`<span style="white-space:normal;overflow-wrap:anywhere;">${value}</span>`,
      file_b: value => html`<span style="white-space:normal;overflow-wrap:anywhere;">${value}</span>`,
      support_pct: value => new Intl.NumberFormat(undefined, {style: "percent", maximumFractionDigits: 1}).format(value),
    },
  }));
}
else display(html`<p>No coupling rows match the current filters. See <a href="health.html">Health</a> for code-maat collection results.</p>`);
```

> ${narr2.body_md}

---

## Code aging chart

```js
const ages = await query(`
  SELECT bucket_start_year, SUM(surviving_loc) AS surviving_loc
  FROM code_age_buckets cab
  JOIN repos r ON r.repo_id = cab.repo_id
  WHERE r.target_id = ?
  GROUP BY 1 ORDER BY 1
`, [target_id]);
const narr3 = await narrative(target_id, "product", "code_aging_chart");
if (!ages.length) {
  display(html`<p>No code-age data was collected. See <a href="health.html">Health</a> for git-of-theseus results.</p>`);
} else display(Plot.plot({
  marks: [
    Plot.barY(ages, { x: d => String(d.bucket_start_year), y: "surviving_loc", fill: "steelblue", tip: true }),
    Plot.text(ages, { x: d => String(d.bucket_start_year), y: "surviving_loc", text: d => d.surviving_loc.toLocaleString(), dy: -8 }),
  ],
  x: { type: "band", label: "Code vintage year" }, y: { label: "Surviving LOC today" },
  marginLeft: 80,
  marginTop: 30,
}));
```

> ${narr3.body_md}

---

## Burndown over time

Code survival over time, grouped by the year the code was introduced. Requires Hercules output.

```js
const burndown = await query(`
  SELECT snapshot_at, vintage_year, SUM(surviving_loc) AS surviving_loc
  FROM burndown_series bs JOIN repos r USING (repo_id)
  WHERE r.target_id = ? GROUP BY snapshot_at, vintage_year ORDER BY snapshot_at, vintage_year
`, [target_id]);
const narr4 = await narrative(target_id, "product", "burndown_over_time");
if (burndown.length) {
  display(Plot.plot({
    marks: [Plot.areaY(burndown, {x: d => new Date(d.snapshot_at), y: "surviving_loc", fill: d => String(d.vintage_year), tip: true})],
    color: {type: "ordinal", legend: true, label: "Vintage"}, y: {label: "Surviving LOC"},
    marginLeft: 80,
  }));
} else {
  display(html`<p>Code-survival data is unavailable. See <a href="health.html">Health</a> for tool results.</p>`);
}
```

> ${narr4.body_md}

---

## Abandoned area register

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
if (abandoned.length) display(Inputs.table(abandoned, { columns: ["repo", "last_commit_at", "last_author", "last_msg"] }));
else display(html`<p>No repositories are currently classified as abandoned. Review classifications in <a href="curation.html">Curation</a>.</p>`);
```

> ${narr5.body_md}

---

## Language inventory

Current language totals are available for repositories discovered through GitHub. Historical technology changes are not collected.

```js
const stacks = await query(`
  SELECT r.name AS repo, r.language_primary, r.languages
  FROM repos r WHERE r.target_id = ? ORDER BY r.name
`, [target_id]);
const narr6 = await narrative(target_id, "product", "tech_stack_drift");
display(Inputs.table(stacks, { columns: ["repo", "language_primary", "languages"] }));
```

> ${narr6.body_md}

```js
display(html`<a href="../${observable.params.target}.html">Target overview</a> · <a href="/index.html">Portfolio</a>`);
```
