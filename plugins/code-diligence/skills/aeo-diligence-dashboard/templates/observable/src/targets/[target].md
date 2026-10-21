---
toc: false
---

# ${target.name}

```js
import {query} from "../data/warehouse.js";
import {ciHealth, codeAge, codeHealth, developmentActivity, ownershipByPerson, peopleByLabel, repositoryHistory, securityPeriods} from "../data/metrics.js";
import {day, personNames} from "../data/labels.js";
import {overview} from "../data/overview.js";

const target_id = observable.params.target;
const target = (await query(`SELECT name, description, last_refreshed_at FROM targets WHERE target_id = ?`, [target_id]))[0];
const refreshed = target.last_refreshed_at
  ? `${day(target.last_refreshed_at)} at ${new Date(target.last_refreshed_at).toLocaleTimeString(undefined, {hour: "numeric", minute: "2-digit"})}`
  : "Not yet refreshed";
const config = await FileAttachment("../data/config.json").json();
const nameOf = await personNames(target_id);
const [repositories, ownership, people, ages, health, ci, activity, security] = await Promise.all([
  repositoryHistory(target_id), ownershipByPerson(target_id), peopleByLabel(target_id),
  codeAge(target_id), codeHealth(target_id), ciHealth(target_id), developmentActivity(target_id), securityPeriods(target_id),
]);
```

<div class="dashboard-metadata" hidden><span class="target-description">${target.description ?? ""}</span><span class="target-refresh-date">${refreshed}</span></div>

```js
display(overview({
  targetId: target_id, target, repositories, ownership, people, ages, health, ci, activity, security,
  labels: config.display_labels[target_id] ?? {}, nameOf, width, invalidation,
}));
```
