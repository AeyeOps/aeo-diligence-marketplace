# Curation

```js
const summary = await FileAttachment("../../data/curation-counts.txt").json();
const hasCounts = summary.target === observable.params.target && summary.identity_needs_review !== null;
const count = value => hasCounts ? value : "Unavailable";
const curationPath = filename => hasCounts ? `${summary.directory}/${filename}` : "Not supplied for this target";
```

<p class="subtitle">Edit these files, then refresh, to change who counts as one person, how contributors are labeled and what type each repository is.</p>

| File | Needs review | Path |
|---|---|---|
| Identity merges | ${count(summary.identity_needs_review)} | ${curationPath("identity-merges.yaml")} |
| Contributor labels | ${count(summary.fte_needs_review)} | ${curationPath("fte-classification.yaml")} |
| Repository types | ${count(summary.repo_needs_review)} | ${curationPath("repo-classification.yaml")} |

${hasCounts ? "" : "Review counts were not supplied for this target. Rebuild with its target ID and curation directory to include them."}
