# Data health — ${observable.params.target}

Signal completeness counts expected tables that contain rows. An empty signal table can mean no matching records or unavailable collection; recorded tool failures below identify collection errors.

```js
import {query} from "../../data/warehouse.js";
const target_id = observable.params.target;
const confidence = await query(`SELECT axis, confidence_class, signal_completeness_pct, missing_sources AS empty_signal_tables FROM axis_confidence WHERE target_id = ? ORDER BY axis`, [target_id]);
const failures = await query(`SELECT repo_id, tool, class, message, occurred_at FROM tool_failures WHERE target_id = ? ORDER BY occurred_at DESC`, [target_id]);
const versions = await query(`SELECT tooling_versions FROM targets WHERE target_id = ?`, [target_id]);
display(Inputs.table(confidence, {format: {
  signal_completeness_pct: value => `${value}%`,
  empty_signal_tables: value => {
    const tables = JSON.parse(value);
    return tables.length ? tables.join(", ") : "None";
  },
}}));
```

## Recorded tool failures

```js
if (failures.length) display(html`<div>${failures.map(failure => html`<details>
  <summary>${failure.tool} · ${failure.repo_id} · ${failure.class} · ${new Date(failure.occurred_at).toISOString()}</summary>
  <pre style="white-space:pre-wrap;overflow-wrap:anywhere;">${failure.message}</pre>
</details>`)}</div>`);
else display(html`<p>No tool failures have been recorded for this target.</p>`);
```

## Tool versions

```js
display(Inputs.table(Object.entries(JSON.parse(versions[0].tooling_versions ?? "{}")).map(([tool, version]) => ({tool, version}))));
```

[Portfolio](/index.html)
