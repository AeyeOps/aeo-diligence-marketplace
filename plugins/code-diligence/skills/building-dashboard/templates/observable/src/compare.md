# Compare targets

```js
import { query } from "./data/warehouse.js";
import * as Plot from "npm:@observablehq/plot";

// The compare page expects the build script to have merged multiple target warehouses
// into the bundled DuckDB. For v1, we merge by ATTACHing each target's .duckdb under a schema name.
const targets = await query(`
  SELECT t.target_id, t.name,
         (SELECT confidence_class FROM axis_confidence WHERE target_id = t.target_id AND axis='people') AS people_conf,
         (SELECT confidence_class FROM axis_confidence WHERE target_id = t.target_id AND axis='product') AS product_conf,
         (SELECT confidence_class FROM axis_confidence WHERE target_id = t.target_id AND axis='process') AS process_conf
  FROM targets t ORDER BY t.name
`);
display(Inputs.table(targets));
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
display(Plot.plot({
  marks: [Plot.barX(headline, { x: "abandoned_repos", y: "target", sort: { y: "x" }, fill: "crimson" })],
  x: { label: "Abandoned repos" },
}));
display(Inputs.table(headline));
```

(More cross-target charts can be added as `code_diligence` is run on more targets and patterns emerge.)
