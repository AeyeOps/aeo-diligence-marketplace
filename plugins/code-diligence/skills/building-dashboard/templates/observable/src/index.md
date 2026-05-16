# Portfolio

```js
import { query } from "./data/warehouse.js";

const targets = await query(`
  SELECT t.target_id, t.name, t.last_refreshed_at,
         (SELECT MIN(confidence_class) FROM axis_confidence WHERE target_id = t.target_id) AS min_conf
  FROM targets t
  ORDER BY t.last_refreshed_at DESC NULLS LAST
`);
```

```js
display(html`<table>
  <thead><tr><th>Target</th><th>Last refresh</th><th>Min confidence</th><th></th></tr></thead>
  <tbody>${targets.map(t => html`<tr>
    <td>${t.name}</td>
    <td>${t.last_refreshed_at?.toString().slice(0,16) ?? "—"}</td>
    <td>${t.min_conf ?? "—"}</td>
    <td><a href="targets/${t.target_id}/">open →</a></td>
  </tr>`)}</tbody>
</table>`);
```
