# Compare targets

```js
import { query } from "./data/warehouse.js";
import * as Plot from "npm:@observablehq/plot";

const targets = await query(`
  SELECT t.target_id, t.name,
         (SELECT confidence_class FROM axis_confidence WHERE target_id = t.target_id AND axis='people') AS people_conf,
         (SELECT confidence_class FROM axis_confidence WHERE target_id = t.target_id AND axis='product') AS product_conf,
         (SELECT confidence_class FROM axis_confidence WHERE target_id = t.target_id AND axis='process') AS process_conf
  FROM targets t ORDER BY t.name
`);
display(Inputs.table(targets, {
  header: {target_id: "Target ID", name: "Name", people_conf: "People", product_conf: "Product", process_conf: "Process"},
  format: {name: value => html`<span style="white-space:normal;overflow-wrap:anywhere;">${value}</span>`},
}));
```

## Headline metrics across targets

```js
const headline = await query(`
  SELECT t.name AS target,
         (SELECT COUNT(*) FROM repos r WHERE r.target_id = t.target_id) AS repos,
         (SELECT COUNT(*) FROM authors a WHERE a.target_id = t.target_id) AS authors,
         (SELECT COUNT(*) FROM repo_classification rc JOIN repos r ON r.repo_id = rc.repo_id
            WHERE r.target_id = t.target_id AND rc.class='abandoned') AS abandoned_repos,
         (SELECT AVG(top_owner_pct) FROM file_metrics fm JOIN repos r ON r.repo_id = fm.repo_id
            WHERE r.target_id = t.target_id) AS avg_top_owner_pct
  FROM targets t ORDER BY t.name
`);
if (headline.some(row => row.abandoned_repos > 0)) display(Plot.plot({
  marks: [Plot.barX(headline, { x: "abandoned_repos", y: "target", sort: { y: "x" }, fill: "crimson" })],
  x: { label: "Abandoned repos" },
  marginLeft: 250,
}));
else display(html`<p>No repository in these targets is labeled abandoned.</p>`);
display(Inputs.table(headline.map(row => ({
  ...row,
  avg_top_owner_pct: row.avg_top_owner_pct === null ? "Not available" : row.avg_top_owner_pct,
})), {
  header: {target: "Target", repos: "Repos", authors: "Authors", abandoned_repos: "Abandoned", avg_top_owner_pct: "Avg. owner share"},
  width: {target: 240, repos: 60, authors: 60, abandoned_repos: 90, avg_top_owner_pct: 140},
  format: {
    target: value => html`<span style="white-space:normal;overflow-wrap:anywhere;">${value}</span>`,
    avg_top_owner_pct: value => typeof value === "number" ? new Intl.NumberFormat(undefined, {style: "percent", maximumFractionDigits: 1}).format(value) : value,
  },
}));
```

File ownership estimates require code-maat results. See each target's Health page when an estimate is unavailable.
