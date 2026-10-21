# Portfolio

```js
import {reportTable} from "./data/tables.js";
import {query} from "./data/warehouse.js";
import {when} from "./data/labels.js";

const targets = await query(`
  SELECT t.target_id, t.name, t.last_refreshed_at,
         (SELECT CASE MAX(CASE confidence_class WHEN 'low' THEN 2 WHEN 'medium' THEN 1 ELSE 0 END) WHEN 2 THEN 'Low' WHEN 1 THEN 'Medium' ELSE 'High' END FROM axis_confidence WHERE target_id = t.target_id) AS min_conf
  FROM targets t
  ORDER BY t.last_refreshed_at DESC NULLS LAST
`);
display(reportTable(targets, {
  columns: ["name", "last_refreshed_at", "min_conf"],
  header: {name: "Target", last_refreshed_at: "Refreshed", min_conf: "Lowest confidence"},
  format: {
    name: (name, index, rows) => html`<a href="targets/${rows[index].target_id}.html">${name}</a>`,
    last_refreshed_at: value => when(value) || "Never",
  },
  select: false,
}));
```
