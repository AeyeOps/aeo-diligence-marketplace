# Portfolio

```js
import { query } from "./data/warehouse.js";

const targets = await query(`
  SELECT t.target_id, t.name, t.last_refreshed_at,
         (SELECT CASE MAX(CASE confidence_class WHEN 'low' THEN 2 WHEN 'medium' THEN 1 ELSE 0 END) WHEN 2 THEN 'low' WHEN 1 THEN 'medium' ELSE 'high' END FROM axis_confidence WHERE target_id = t.target_id) AS min_conf
  FROM targets t
  ORDER BY t.last_refreshed_at DESC NULLS LAST
`);
```

```js
display(html`<table>
  <thead><tr><th>Target</th><th>Last refresh</th><th>Min confidence</th><th></th></tr></thead>
  <tbody>${targets.map(t => html`<tr>
    <td>${t.name}</td>
    <td>${t.last_refreshed_at ? new Date(t.last_refreshed_at).toLocaleString() : null ?? "—"}</td>
    <td>${t.min_conf ?? "—"}</td>
    <td><a href="targets/${t.target_id}.html">open →</a></td>
  </tr>`)}</tbody>
</table>`);
```
