# ${target.name}

```js
import {query, axisConfidence} from "../data/warehouse.js";
import {missingSources, when} from "../data/labels.js";

const target_id = observable.params.target;
const target = (await query(`SELECT name, description, last_refreshed_at FROM targets WHERE target_id = ?`, [target_id]))[0];
const axes = await Promise.all(["people", "product", "process"].map(async axis => {
  const confidence = await axisConfidence(target_id, axis);
  return {axis, confidence_class: confidence.confidence_class, missing: missingSources(confidence).join(", ") || "None"};
}));
```

<p class="subtitle">${target.description ?? ""}${target.description ? " · " : ""}Refreshed ${when(target.last_refreshed_at) || "never"}</p>

```js
display(Inputs.table(axes, {
  columns: ["axis", "confidence_class", "missing"],
  header: {axis: "Area", confidence_class: "Confidence", missing: "Missing sources"},
  format: {
    axis: axis => html`<a href="${target_id}/${axis}.html">${axis[0].toUpperCase() + axis.slice(1)}</a>`,
    confidence_class: value => value[0].toUpperCase() + value.slice(1),
  },
  select: false,
}));
```

<p class="caption">Confidence reflects how many expected sources are present for each area.</p>
