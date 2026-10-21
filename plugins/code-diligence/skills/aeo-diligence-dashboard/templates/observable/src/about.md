# About this dashboard

[code-diligence](https://github.com/AeyeOps/aeo-diligence-marketplace) builds this dashboard from git history, open-source analysis tools (Repowise, git-truck, git-fame, code-maat, Hercules and git-of-theseus) and, when a target enables them, GitHub and AWS Inspector data. Each card names the tool its numbers come from.

## Development activity

Monthly commit counts use the collected Git author dates. Added and removed LOC count changed lines in files selected by the same git-of-theseus filename catalog as the current code-size measure. Commit counts include all collected commits; the two measures have separate scales.

## Confidence levels

- High: at least 80% of expected sources are present.
- Medium: 40% to 79% are present.
- Low: fewer than 40% are present.

A source is present when it has data. A GitHub source also counts when it was collected without a failure, because an empty result there means the feature is not used. Confidence does not measure repository coverage, accuracy or agreement between tools. Health lists current collection failures.

## Curation

Three YAML files in the target's curation folder hold analyst decisions, and each refresh applies them:

- `identity-merges.yaml` merges the emails of one person.
- `fte-classification.yaml` labels each contributor as an employee, contractor or bot.
- `repo-classification.yaml` sets each repository's type.

## Tool versions

```js
import {reportTable} from "./data/tables.js";
import { query } from "./data/warehouse.js";
const versions = await query(`SELECT target_id, name, tooling_versions FROM targets ORDER BY name`);
for (const target of versions) {
  display(html`<h3>${target.name}</h3>`);
  if (target.tooling_versions === null) display(html`<p>Tool versions have not been recorded.</p>`);
  else display(reportTable(Object.entries(JSON.parse(target.tooling_versions)).map(([tool, version]) => ({tool, version})), {select: false}));
}
```
