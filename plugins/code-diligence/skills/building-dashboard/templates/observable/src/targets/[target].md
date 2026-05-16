# ${observable.params.target}

```js
import { query, axisConfidence } from "../data/warehouse.js";

const target_id = observable.params.target;
const target = (await query(`SELECT name, description, last_refreshed_at FROM targets WHERE target_id = ?`, [target_id]))[0];
const axes = ["people", "product", "process"];
const confidences = Object.fromEntries(
  await Promise.all(axes.map(async a => [a, await axisConfidence(target_id, a)]))
);
const review_counts = await query(`
  SELECT 'identity' AS k, 0 AS n  -- placeholder; real count comes from curation YAML reader, not warehouse
`);
```

**${target.name}** — last refreshed ${target.last_refreshed_at?.toString().slice(0,16) ?? "never"}

${target.description ?? ""}

## Confidence

```js
display(html`<div style="display:flex; gap:1rem;">
  ${axes.map(a => html`<div style="border:1px solid #ccc; padding:0.5rem 1rem; border-radius:4px;">
    <strong>${a}</strong><br>
    confidence: <span style="color:${confidences[a].confidence_class === 'high' ? 'green' : confidences[a].confidence_class === 'medium' ? 'orange' : 'red'}">${confidences[a].confidence_class}</span><br>
    completeness: ${confidences[a].signal_completeness_pct?.toFixed?.(0) ?? "—"}%
  </div>`)}
</div>`);
```

## Axes

- [People](people) — bus factor, ownership, attrition
- [Product](product) — hotspots, coupling, code aging
- [Process](process) — DORA, review discipline, CI health
- [Repos](repos) — full inventory
