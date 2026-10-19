# Repos

```js
import {query} from "../../data/warehouse.js";
import {count, day, repoClassLabel, targetName} from "../../data/labels.js";
const target_id = observable.params.target;
const name = await targetName(target_id);
const repos = await query(`
  SELECT r.name, r.last_commit_at, r.is_archived,
         COALESCE(rc.class, 'unknown') AS class,
         (SELECT COUNT(*) FROM commits_fact cf WHERE cf.repo_id = r.repo_id) AS commits
  FROM repos r LEFT JOIN repo_classification rc ON rc.repo_id = r.repo_id
  WHERE r.target_id = ? ORDER BY r.name
`, [target_id]);
```

<p class="subtitle">${name}</p>

```js
display(Inputs.table(repos, {
  columns: ["name", "class", "commits", "last_commit_at", "is_archived"],
  header: {name: "Repository", class: "Type", commits: "Commits", last_commit_at: "Last commit", is_archived: "Archived"},
  format: {class: repoClassLabel, commits: count, last_commit_at: day, is_archived: value => value ? "Yes" : "No"},
  select: false,
}));
```
