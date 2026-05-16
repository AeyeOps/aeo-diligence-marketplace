# People — ${observable.params.target}

```js
import { query, narrative } from "../../data/warehouse.js";
import * as Plot from "npm:@observablehq/plot";
const target_id = observable.params.target;
```

## Bus factor map

```js
const bus_factor_rows = await query(`
  SELECT r.name AS repo,
         COUNT(DISTINCT cf.author_email) AS contributors,
         (SELECT COUNT(DISTINCT cf2.author_email)
          FROM commits_fact cf2
          WHERE cf2.repo_id = r.repo_id
          GROUP BY cf2.repo_id
          HAVING SUM(cf2.lines_added + cf2.lines_removed) >= 0.5 * (
            SELECT SUM(lines_added + lines_removed) FROM commits_fact WHERE repo_id = r.repo_id
          )
         ) AS bus_factor_estimate
  FROM repos r
  JOIN commits_fact cf ON cf.repo_id = r.repo_id
  JOIN repo_classification rc ON rc.repo_id = r.repo_id
  WHERE r.target_id = ? AND rc.class IN ('production', 'tooling')
  GROUP BY r.repo_id, r.name
  ORDER BY bus_factor_estimate ASC NULLS FIRST
`, [target_id]);
const narr = await narrative(target_id, "people", "bus_factor_map");
```

```js
display(Plot.plot({
  marks: [
    Plot.barX(bus_factor_rows, {
      x: "bus_factor_estimate", y: "repo", sort: { y: "x" },
      fill: d => d.bus_factor_estimate <= 1 ? "crimson" : d.bus_factor_estimate <= 2 ? "orange" : "steelblue",
      tip: true,
    }),
  ],
  x: { label: "Min FTEs to cover 50% of code knowledge" },
  y: { label: null },
  height: Math.max(120, 24 * bus_factor_rows.length),
}));
```

> ${narr.body_md}

---

## Knowledge concentration heatmap

```js
const conc_rows = await query(`
  SELECT r.name AS repo,
         100.0 * MAX(os.owned_loc) / NULLIF(SUM(os.owned_loc), 0) AS top1_pct
  FROM repos r
  JOIN ownership_share os ON os.repo_id = r.repo_id AND os.source = 'git-fame'
  WHERE r.target_id = ?
  GROUP BY r.repo_id, r.name
  ORDER BY top1_pct DESC
`, [target_id]);
const narr2 = await narrative(target_id, "people", "knowledge_concentration");
display(Plot.plot({
  marks: [Plot.barX(conc_rows, { x: "top1_pct", y: "repo", sort: { y: "x" }, fill: d => d.top1_pct >= 60 ? "crimson" : "steelblue", tip: true })],
  x: { label: "% owned by top-1 author", domain: [0, 100] },
}));
```

> ${narr2.body_md}

---

## Contributor activity timeline

```js
const activity_rows = await query(`
  SELECT DATE_TRUNC('month', cf.author_date) AS month,
         COALESCE(cc.class, 'unknown') AS class,
         COUNT(DISTINCT cf.author_email) AS active_authors
  FROM commits_fact cf
  JOIN repos r ON r.repo_id = cf.repo_id
  LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = cf.author_email
  LEFT JOIN contributor_classification cc ON cc.target_id = r.target_id AND cc.author_email = COALESCE(im.canonical_email, cf.author_email)
  WHERE r.target_id = ?
  GROUP BY 1, 2
  ORDER BY 1
`, [target_id]);
const narr3 = await narrative(target_id, "people", "contributor_activity_timeline");
display(Plot.plot({
  marks: [Plot.areaY(activity_rows, { x: "month", y: "active_authors", fill: "class", tip: true })],
  color: { legend: true },
  height: 240,
}));
```

> ${narr3.body_md}

---

## Communication graph

```js
// Two authors are "linked" if they've co-edited the same file in the same month.
// Force-directed layout via D3.
const edges = await query(`
  WITH file_author_month AS (
    SELECT DISTINCT cfa.repo_id,
           DATE_TRUNC('month', cfa.author_date) AS m,
           cfa.file_path,
           cfa.author_email
    FROM commit_file_authors cfa
    JOIN repos r ON r.repo_id = cfa.repo_id
    WHERE r.target_id = ?
  )
  SELECT a.author_email AS source, b.author_email AS target, COUNT(*) AS weight
  FROM file_author_month a JOIN file_author_month b
    ON a.repo_id = b.repo_id AND a.m = b.m AND a.file_path = b.file_path
   AND a.author_email < b.author_email
  GROUP BY 1, 2 HAVING COUNT(*) >= 1
  ORDER BY weight DESC LIMIT 100
`, [target_id]);
const narr4 = await narrative(target_id, "people", "communication_graph");
```

```js
// Render with D3 force layout — implementer fills in standard force-graph code from D3 examples
display(html`<p><em>(force-directed graph — ${edges.length} edges)</em></p>`);
```

> ${narr4.body_md}

---

## Hero / dependency register

```js
const heroes = await query(`
  SELECT r.name AS repo, fm.path AS file, fm.top_owner_email AS owner, fm.top_owner_pct AS owned_pct
  FROM file_metrics fm
  JOIN repos r ON r.repo_id = fm.repo_id
  WHERE r.target_id = ? AND fm.top_owner_pct >= 0.9
  ORDER BY fm.top_owner_pct DESC, fm.revisions DESC
  LIMIT 50
`, [target_id]);
const narr5 = await narrative(target_id, "people", "hero_dependency_register");
display(Inputs.table(heroes, { columns: ["repo", "file", "owner", "owned_pct"] }));
```

> ${narr5.body_md}
