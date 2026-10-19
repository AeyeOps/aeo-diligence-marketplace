# ${observable.params.target}

```js
import { query, axisConfidence } from "../data/warehouse.js";

const target_id = observable.params.target;
const target = (await query(`SELECT name, description, last_refreshed_at FROM targets WHERE target_id = ?`, [target_id]))[0];
const axes = ["people", "product", "process"];
const confidences = Object.fromEntries(
  await Promise.all(axes.map(async a => [a, await axisConfidence(target_id, a)]))
);
```

**${target.name}** — last refreshed ${target.last_refreshed_at ? new Date(target.last_refreshed_at).toLocaleString() : null ?? "never"}

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

## Explore the evidence

```js
display(html`<nav aria-label="Target sections"><ul>${["people", "product", "process", "repos", "curation", "health"].map(section => html`<li><a href="${target_id}/${section}.html">${section[0].toUpperCase() + section.slice(1)}</a></li>`)}</ul></nav>`);
```

[All targets](/index.html)
