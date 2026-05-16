# Repos — ${observable.params.target}

```js
import { query } from "../../data/warehouse.js";
const target_id = observable.params.target;
const repos = await query(`
  SELECT r.repo_id, r.name, r.last_commit_at, r.is_archived,
         COALESCE(rc.class, 'unknown') AS class,
         (SELECT COUNT(*) FROM commits_fact cf WHERE cf.repo_id = r.repo_id) AS commits
  FROM repos r LEFT JOIN repo_classification rc ON rc.repo_id = r.repo_id
  WHERE r.target_id = ? ORDER BY r.name
`, [target_id]);
display(Inputs.table(repos, { columns: ["name", "class", "commits", "last_commit_at", "is_archived"] }));
```
