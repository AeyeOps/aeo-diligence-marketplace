# ${target.name}

```js
import {query, axisConfidence, headlines} from "../data/warehouse.js";
import {confidenceLine, when} from "../data/labels.js";

const target_id = observable.params.target;
const target = (await query(`SELECT name, description, last_refreshed_at FROM targets WHERE target_id = ?`, [target_id]))[0];
const config = await FileAttachment("../data/config.json").json();
const cards = (await headlines(target_id))
  .filter(card => card.section_key !== "working_pattern_signals" || config.allow_working_pattern_card);
const confidence = Object.fromEntries(await Promise.all(
  ["people", "product", "process"].map(async axis => [axis, await axisConfidence(target_id, axis)])
));

function area(axis) {
  return html`<div><p class="subtitle">${confidenceLine(confidence[axis])}</p>
  <dl class="headlines">${cards.filter(card => card.axis === axis).flatMap(card => [
    html`<dt><a href="${target_id}/${axis}.html#${card.anchor}">${card.title}</a></dt>`,
    html`<dd>${card.headline}</dd>`,
  ])}</dl></div>`;
}
```

<p class="subtitle">${target.description ?? ""}${target.description ? " · " : ""}Refreshed ${when(target.last_refreshed_at) || "never"}</p>

## People

```js
display(area("people"));
```

## Product

```js
display(area("product"));
```

## Process

```js
display(area("process"));
```
