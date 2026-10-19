# People

```js
import {query, narrative, axisConfidence} from "../../data/warehouse.js";
import {CLASS_ORDER, classLabel, confidenceLine, count, personNames, pct, targetName, wrap} from "../../data/labels.js";
import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
const target_id = observable.params.target;
const conf = await axisConfidence(target_id, "people");
const name = await targetName(target_id);
const nameOf = await personNames(target_id);
```

<p class="subtitle">${name} · ${confidenceLine(conf)}</p>

## Bus factor map

<p class="finding">${narr.body}</p>

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
  GROUP BY totals.repo_id, totals.repo ORDER BY bus_factor_estimate, totals.repo
`, [target_id]);
const narr = await narrative(target_id, "people", "bus_factor_map");
display(Inputs.table(bus_factor_rows.map(row => ({...row, bus_factor_estimate: row.bus_factor_estimate ?? "Not established"})), {
  columns: ["repo", "confirmed_ftes", "bus_factor_estimate"],
  header: {repo: "Repository", confirmed_ftes: "Confirmed employees", bus_factor_estimate: "Bus factor"},
}));
```

<p class="caption">Employees whose combined surviving lines (git-fame) reach half of each production or tooling repository, after identity merges. Unlabeled contributors are not counted as employees.</p>

---

## Knowledge concentration heatmap

<p class="finding">${narr2.body}</p>

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
  ), ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY owned_loc DESC, author) AS rank,
           SUM(owned_loc) OVER (PARTITION BY repo_id) AS total_loc
    FROM ownership
  )
  SELECT repo, author AS top_owner, 100.0 * owned_loc / NULLIF(total_loc, 0) AS top1_pct
  FROM ranked WHERE rank = 1 ORDER BY top1_pct DESC
`, [target_id]);
const narr2 = await narrative(target_id, "people", "knowledge_concentration");
display(Plot.plot({
  marks: [
    Plot.barX(conc_rows, {x: "top1_pct", y: "repo", sort: {y: "-x"}, fill: "var(--theme-foreground-focus)", tip: true}),
    Plot.text(conc_rows, {x: "top1_pct", y: "repo", text: row => `${row.top1_pct.toFixed(1)}% · ${nameOf(row.top_owner)}`, textAnchor: "start", dx: 6, fill: "currentColor"}),
    Plot.ruleX([0]),
  ],
  x: {domain: [0, 100], label: "Largest contributor's share of surviving lines (%)"},
  y: {label: null},
  marginLeft: 190,
  marginRight: 230,
  height: 48 * conc_rows.length + 50,
}));
```

<p class="caption">Share of each repository's surviving lines (git-fame) held by its largest contributor, after identity merges.</p>

---

## Contributor activity timeline

<p class="finding">${narr3.body}</p>

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
const monthly_totals = d3.rollup(activity_rows, rows => d3.sum(rows, row => row.active_authors), row => +row.month);
const peak = d3.max(monthly_totals.values()) ?? 1;
display(Plot.plot({
  marks: [
    Plot.rectY(activity_rows, {x: "month", interval: "month", y: "active_authors", fill: row => classLabel(row.class), tip: true}),
    Plot.ruleY([0]),
  ],
  color: {legend: true, domain: CLASS_ORDER, scheme: "observable10"},
  x: {label: null},
  y: {label: "People active", ticks: peak, tickFormat: "d"},
  height: 240,
}));
```

<p class="caption">Distinct people committing each month, after identity merges, by their confirmed label.</p>

---

## Communication graph

<p class="finding">${narr4.body}</p>

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
const graph_width = 720, graph_height = Math.min(360, 120 + 60 * nodes.length);
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(node => node.id).distance(120))
  .force("charge", d3.forceManyBody().strength(-220))
  .force("center", d3.forceCenter(graph_width / 2, graph_height / 2)).stop();
for (let i = 0; i < 200; i++) simulation.tick();
const graph = d3.create("svg").attr("viewBox", [0, 0, graph_width, graph_height]).attr("width", graph_width).attr("style", "max-width:100%;height:auto;").attr("role", "img").attr("aria-label", "Contributors linked by shared file changes");
graph.append("g").attr("stroke", "var(--theme-foreground-faint)").selectAll("line").data(links).join("line")
  .attr("x1", edge => edge.source.x).attr("y1", edge => edge.source.y)
  .attr("x2", edge => edge.target.x).attr("y2", edge => edge.target.y)
  .attr("stroke-width", edge => Math.max(1, Math.log2(edge.weight + 1) * 2))
  .append("title").text(edge => `${nameOf(edge.source.id)} and ${nameOf(edge.target.id)}: ${count(edge.weight)} shared file-months`);
graph.append("g").attr("fill", "var(--theme-foreground-focus)").selectAll("circle").data(nodes).join("circle")
  .attr("cx", node => node.x).attr("cy", node => node.y).attr("r", 7);
graph.append("g").attr("fill", "currentColor").attr("font-size", 12).selectAll("text").data(nodes).join("text")
  .attr("x", node => node.x + 11).attr("y", node => node.y + 4).text(node => nameOf(node.id));
display(graph.node());
```

<p class="caption">People linked when they changed the same file in the same month; line width grows with those shared file-months. Co-editing is not evidence of communication.</p>

---

## Hero / dependency register

<p class="finding">${narr5.body}</p>

```js
const heroes = await query(`
  SELECT r.name AS repo, fm.path AS file,
         COALESCE(im.canonical_email, fm.top_owner_email) AS owner,
         fm.top_owner_pct AS owned_pct, fm.revisions
  FROM file_metrics fm
  JOIN repos r ON r.repo_id = fm.repo_id
  LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = fm.top_owner_email
  WHERE r.target_id = ? AND fm.top_owner_pct >= 0.9
  ORDER BY fm.top_owner_pct DESC, fm.revisions DESC
  LIMIT 50
`, [target_id]);
const narr5 = await narrative(target_id, "people", "hero_dependency_register");
display(Inputs.table(heroes, {
  columns: ["file", "repo", "owner", "owned_pct", "revisions"],
  header: {file: "File", repo: "Repository", owner: "Owner", owned_pct: "Owner share", revisions: "Changes"},
  format: {file: wrap, repo: wrap, owner: value => nameOf(value), owned_pct: pct, revisions: count},
  width: {file: "42%"},
}));
```

<p class="caption">Files where one person made at least 90% of the added lines over their history (code-maat), most-changed first, top 50.</p>
