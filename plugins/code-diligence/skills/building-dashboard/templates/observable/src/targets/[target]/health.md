# Data health — ${observable.params.target}

Use this page to distinguish missing inputs from an absence of findings.

```js
import {query} from "../../data/warehouse.js";
const target_id = observable.params.target;
const confidence = await query(`SELECT axis, confidence_class, signal_completeness_pct, missing_sources FROM axis_confidence WHERE target_id = ? ORDER BY axis`, [target_id]);
const failures = await query(`SELECT repo_id, tool, class, message, occurred_at FROM tool_failures WHERE target_id = ? ORDER BY occurred_at DESC`, [target_id]);
const versions = await query(`SELECT tooling_versions FROM targets WHERE target_id = ?`, [target_id]);
display(Inputs.table(confidence));
```

## Recorded tool failures

```js
if (failures.length) display(Inputs.table(failures));
else display(html`<p>No tool failures have been recorded for this target.</p>`);
```

## Tool versions

```js
display(Inputs.table(Object.entries(JSON.parse(versions[0].tooling_versions ?? "{}")).map(([tool, version]) => ({tool, version}))));
```

[Portfolio](/index.html)
