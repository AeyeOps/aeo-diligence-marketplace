# People — ${observable.params.target}

```js
import { query, narrative } from "../../data/warehouse.js";
import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
const target_id = observable.params.target;
```

## Bus factor map

This estimate counts confirmed FTEs needed to cover 50% of attributed LOC in production and tooling repositories. It uses git-fame ownership and confirmed identity merges. Unclassified contributors are not assumed to be employees; a missing estimate means the available FTE ownership does not establish that coverage.

```js
const bus_factor_rows = await query(`
  WITH ownership AS (
    SELECT r.repo_id, r.name AS repo,
           COALESCE(im.canonical_email, os.author_email) AS author,
           SUM(os.owned_loc) AS owned_loc,
           cc.class AS contributor_class
    FROM repos r
    JOIN ownership_share os ON os.repo_id = r.repo_id AND os.source = 'git-fame'
    LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = os.author_email
    LEFT JOIN contributor_classification cc ON cc.target_id = r.target_id AND cc.author_email = COALESCE(im.canonical_email, os.author_email)
    JOIN repo_classification rc ON rc.repo_id = r.repo_id
    WHERE r.target_id = ? AND rc.class IN ('production', 'tooling')
    GROUP BY r.repo_id, r.name, author, cc.class
  ), totals AS (
    SELECT repo_id, repo, SUM(owned_loc) AS total_loc FROM ownership GROUP BY repo_id, repo
  ), ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY owned_loc DESC, author) AS author_rank,
           SUM(owned_loc) OVER (PARTITION BY repo_id ORDER BY owned_loc DESC, author) AS cumulative_loc
    FROM ownership WHERE contributor_class = 'fte'
  )
  SELECT totals.repo, COUNT(ranked.author) AS confirmed_ftes,
         MIN(CASE WHEN cumulative_loc >= totals.total_loc * 0.5 AND totals.total_loc > 0 THEN author_rank END) AS bus_factor_estimate
  FROM totals LEFT JOIN ranked ON ranked.repo_id = totals.repo_id
  GROUP BY totals.repo_id, totals.repo ORDER BY bus_factor_estimate
`, [target_id]);
const narr = await narrative(target_id, "people", "bus_factor_map");
```

```js
if (!bus_factor_rows.length) {
  display(html`<p>No ownership data matches the repository classifications. Review <a href="curation.html">Curation</a> and <a href="health.html">Health</a>.</p>`);
} else display(Plot.plot({
  marks: [
    Plot.barX(bus_factor_rows, {
      x: "bus_factor_estimate", y: "repo", sort: { y: "x" },
      fill: d => d.bus_factor_estimate <= 1 ? "crimson" : d.bus_factor_estimate <= 2 ? "orange" : "steelblue",
      tip: true,
    }),
  ],
  x: { label: "Confirmed FTEs covering 50% of attributed LOC" },
  y: { label: null },
  height: Math.max(120, 24 * bus_factor_rows.length),
}));
display(Inputs.table(bus_factor_rows, {columns: ["repo", "confirmed_ftes", "bus_factor_estimate"]}));
```

> ${narr.body_md}

---

## Knowledge concentration heatmap

```js
const conc_rows = await query(`
  WITH ownership AS (
    SELECT r.repo_id, r.name AS repo,
           COALESCE(im.canonical_email, os.author_email) AS author,
           SUM(os.owned_loc) AS owned_loc
    FROM repos r
    JOIN ownership_share os ON os.repo_id = r.repo_id AND os.source = 'git-fame'
    LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = os.author_email
    WHERE r.target_id = ? GROUP BY r.repo_id, r.name, author
  )
  SELECT repo, 100.0 * MAX(owned_loc) / NULLIF(SUM(owned_loc), 0) AS top1_pct
  FROM ownership GROUP BY repo_id, repo
  ORDER BY top1_pct DESC
`, [target_id]);
const narr2 = await narrative(target_id, "people", "knowledge_concentration");
if (!conc_rows.length) {
  display(html`<p>No git-fame ownership data is available. See <a href="health.html">Health</a> for tool results.</p>`);
} else display(Plot.plot({
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
         COUNT(DISTINCT COALESCE(im.canonical_email, cf.author_email)) AS active_authors
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
  marks: [Plot.rectY(activity_rows, { x: "month", interval: "month", y: "active_authors", fill: "class", tip: true })],
  color: { legend: true },
  height: 240,
}));
```

> ${narr3.body_md}

---

## Communication graph

```js
const edges = await query(`
  WITH file_author_month AS (
    SELECT DISTINCT cfa.repo_id,
           DATE_TRUNC('month', cfa.author_date) AS m,
           cfa.file_path,
           COALESCE(im.canonical_email, cfa.author_email) AS author_email
    FROM commit_file_authors cfa
    JOIN repos r ON r.repo_id = cfa.repo_id
    LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = cfa.author_email
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
const nodes = Array.from(new Set(edges.flatMap(edge => [edge.source, edge.target])), id => ({id}));
const links = edges.map(edge => ({...edge}));
const width = 860, height = 400;
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(node => node.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-160))
  .force("center", d3.forceCenter(width / 2, height / 2)).stop();
for (let i = 0; i < 160; i++) simulation.tick();
const graph = d3.create("svg").attr("viewBox", [0, 0, width, height]).attr("role", "img").attr("aria-label", "Contributors linked by shared file changes");
graph.append("g").attr("stroke", "#94a3b8").selectAll("line").data(links).join("line")
  .attr("x1", edge => edge.source.x).attr("y1", edge => edge.source.y)
  .attr("x2", edge => edge.target.x).attr("y2", edge => edge.target.y)
  .attr("stroke-width", edge => Math.sqrt(edge.weight));
graph.append("g").attr("fill", "steelblue").selectAll("circle").data(nodes).join("circle")
  .attr("cx", node => node.x).attr("cy", node => node.y).attr("r", 6)
  .append("title").text(node => node.id);
graph.append("g").attr("fill", "currentColor").attr("font-size", 11).selectAll("text").data(nodes).join("text")
  .attr("x", node => node.x + 9).attr("y", node => node.y + 4).text(node => node.id);
display(nodes.length ? graph.node() : html`<p>No shared file changes were found for this target.</p>`);
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

```js
display(html`<a href="../${observable.params.target}.html">Target overview</a> · <a href="/index.html">Portfolio</a>`);
```
