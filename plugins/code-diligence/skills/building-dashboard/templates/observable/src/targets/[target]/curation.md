# Curation — ${observable.params.target}

```js
const summary = await FileAttachment("../../data/curation-counts.txt").json();
const hasCounts = summary.target === observable.params.target && summary.identity_needs_review !== null;
const count = value => hasCounts ? value : "Unavailable";
```

These three YAML files are the source of truth for analyst overrides. Edit them directly between ingest runs; subsequent runs respect your edits.

| File | Needs review | Path |
|---|---|---|
| Identity merges | ${count(summary.identity_needs_review)} | `<curation_dir>/identity-merges.yaml` |
| FTE classification | ${count(summary.fte_needs_review)} | `<curation_dir>/fte-classification.yaml` |
| Repo classification | ${count(summary.repo_needs_review)} | `<curation_dir>/repo-classification.yaml` |

${hasCounts ? "" : "Review counts were not supplied for this target. Rebuild with its target ID and curation directory to include them."}

(The actual filesystem path is what you set in your target's settings file under `storage.curation_dir`.)

```js
display(html`<a href="../${observable.params.target}.html">Target overview</a> · <a href="/index.html">Portfolio</a>`);
```
