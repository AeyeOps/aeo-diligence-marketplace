# Curation — ${observable.params.target}

```js
const summary = await FileAttachment("../../data/curation-counts.txt").json();
```

These three YAML files are the source of truth for analyst overrides. Edit them directly between ingest runs; subsequent runs respect your edits.

| File | Needs review | Path |
|---|---|---|
| Identity merges | ${summary.identity_needs_review} | `<curation_dir>/identity-merges.yaml` |
| FTE classification | ${summary.fte_needs_review} | `<curation_dir>/fte-classification.yaml` |
| Repo classification | ${summary.repo_needs_review} | `<curation_dir>/repo-classification.yaml` |

(The actual filesystem path is what you set in your target's settings file under `storage.curation_dir`.)
