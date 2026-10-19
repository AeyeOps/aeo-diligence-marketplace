# Curation — ${observable.params.target}

```js
const summary = await FileAttachment("../../data/curation-counts.txt").json();
const hasCounts = summary.target === observable.params.target && summary.identity_needs_review !== null;
const count = value => hasCounts ? value : "Unavailable";
const curationPath = filename => hasCounts ? `${summary.directory}/${filename}` : "Not supplied for this target";
```

These three YAML files are the source of truth for analyst overrides. Edit them directly between ingest runs; subsequent runs respect your edits.

| File | Needs review | Path |
|---|---|---|
| Identity merges | ${count(summary.identity_needs_review)} | ${curationPath("identity-merges.yaml")} |
| FTE classification | ${count(summary.fte_needs_review)} | ${curationPath("fte-classification.yaml")} |
| Repo classification | ${count(summary.repo_needs_review)} | ${curationPath("repo-classification.yaml")} |

${hasCounts ? "" : "Review counts were not supplied for this target. Rebuild with its target ID and curation directory to include them."}

Paths refer to the machine that built this dashboard.

```js
display(html`<a href="../${observable.params.target}.html">Target overview</a> · <a href="/index.html">Portfolio</a>`);
```
