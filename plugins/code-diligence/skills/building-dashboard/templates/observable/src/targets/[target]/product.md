# Product — ${observable.params.target}

```js
import { query, narrative } from "../../data/warehouse.js";
import * as Plot from "npm:@observablehq/plot";
const target_id = observable.params.target;
```

## Hotspot map

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
display(Plot.plot({
  marks: [
    Plot.dot(hotspots, {
      x: "revisions", y: "complexity_proxy",
      r: d => Math.sqrt(d.hotspot_score),
      fill: d => d.hotspot_score > 100 ? "crimson" : "steelblue",
      stroke: "white", strokeWidth: 0.5,
      title: d => `${d.repo}/${d.path}\nrev=${d.revisions} cmplx=${d.complexity_proxy?.toFixed(1)}`,
      tip: true,
    }),
  ],
  x: { label: "Revisions", type: "log" },
  y: { label: "Complexity proxy" },
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
display(Inputs.table(couplings, { columns: ["repo_id", "file_a", "file_b", "support_pct", "lift"] }));
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
display(Plot.plot({
  marks: [Plot.areaY(ages, { x: "bucket_start_year", y: "surviving_loc", fill: "steelblue" })],
  x: { label: "Code vintage year" }, y: { label: "Surviving LOC today" },
}));
```

> ${narr3.body_md}

---

## Burndown over time

(Phase 2 — depends on hercules data in `burndown_series`. Quick-tier shows a placeholder.)

```js
const has_burndown = (await query(`
  SELECT COUNT(*) AS n FROM burndown_series bs JOIN repos r ON r.repo_id = bs.repo_id
  WHERE r.target_id = ?
`, [target_id]))[0].n;
const narr4 = await narrative(target_id, "product", "burndown_over_time");
if (has_burndown > 0) {
  // Render burndown stacked area; same shape as code aging chart but per-snapshot
  display(html`<p>(burndown chart here)</p>`);
} else {
  display(html`<p><em>Data unavailable until full-tier ingest.</em></p>`);
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
display(Inputs.table(abandoned, { columns: ["repo", "last_commit_at", "last_author", "last_msg"] }));
```

> ${narr5.body_md}

---

## Tech-stack inventory + drift

```js
const stacks = await query(`
  SELECT r.name AS repo, r.language_primary, r.languages
  FROM repos r WHERE r.target_id = ? ORDER BY r.name
`, [target_id]);
const narr6 = await narrative(target_id, "product", "tech_stack_drift");
display(Inputs.table(stacks, { columns: ["repo", "language_primary", "languages"] }));
```

> ${narr6.body_md}
