# Health

```js
import {reportTable} from "../../data/tables.js";
import {query} from "../../data/warehouse.js";
import {missingSources, targetName, when, wrap} from "../../data/labels.js";
const target_id = observable.params.target;
const name = await targetName(target_id);
const confidence = (await query(`SELECT axis, confidence_class, signal_completeness_pct, missing_sources FROM axis_confidence WHERE target_id = ? ORDER BY axis`, [target_id]))
  .map(row => ({...row, missing: missingSources(row).join(", ") || "None"}));
const failures = await query(`SELECT repo_id, tool, class, message, occurred_at FROM tool_failures WHERE target_id = ? ORDER BY occurred_at DESC`, [target_id]);
const versions = await query(`SELECT tooling_versions FROM targets WHERE target_id = ?`, [target_id]);
const repoName = repo_id => repo_id ? repo_id.split("/").slice(1).join("/") : "All repositories";
```

<p class="subtitle">${name}</p>

## Sources

```js
display(reportTable(confidence, {
  columns: ["axis", "confidence_class", "signal_completeness_pct", "missing"],
  header: {axis: "Area", confidence_class: "Confidence", signal_completeness_pct: "Sources present", missing: "Missing"},
  format: {
    axis: value => value[0].toUpperCase() + value.slice(1),
    confidence_class: value => value[0].toUpperCase() + value.slice(1),
    signal_completeness_pct: value => `${Math.round(value)}%`,
  },
  select: false,
}));
```

<p class="caption">A source is present when it has data. A GitHub source also counts when it was collected without a failure, because an empty result there means the feature is not used.</p>

## Tool failures

```js
if (failures.length) display(reportTable(failures, {
  columns: ["tool", "repo_id", "class", "occurred_at", "message"],
  header: {tool: "Tool", repo_id: "Repository", class: "Problem", occurred_at: "When", message: "Message"},
  format: {repo_id: repoName, class: value => value.replace("_", " "), occurred_at: when, message: wrap},
  width: {message: "45%"},
  select: false,
}));
else display(html`<p>Every tool completed on its last run.</p>`);
```

## Tool versions

```js
display(reportTable(Object.entries(JSON.parse(versions[0].tooling_versions ?? "{}")).map(([tool, version]) => ({tool, version})), {
  header: {tool: "Tool", version: "Version"},
  select: false,
}));
```
