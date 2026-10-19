# Product axis — 7 cards

| section_key | Evidence and interpretation |
|---|---|
| `hotspot_map` | Revision counts from `file_metrics` for files that exist at HEAD in production and tooling repositories. The displayed score multiplies revisions by `complexity_proxy` only where a value exists; the current pipeline does not populate complexity. |
| `code_health` | Repowise's own ratings: per-repository health scores from 1 to 10, higher is healthier, from `repowise_health`, and finding counts by Repowise severity from `repowise_findings`. Findings without a severity are dead-code results. |
| `hidden_coupling_matrix` | Code-maat file pairs with shared-commit count, support and lift from walker facts. The card shows lift above 1.5 and support above 0.05. |
| `code_aging_chart` | Current surviving LOC by introduction year from git-of-theseus, counting only the file types it recognizes as source. JSON, Markdown and other data files are left out, so its totals run below burndown's. |
| `burndown_over_time` | Per-repository surviving LOC at each snapshot, grouped by vintage year, from hercules, counting every tracked file. Repositories have different sample dates; their isolated samples are not a combined target trend. |
| `abandoned_area_register` | Repositories with confirmed `abandoned` classification and their last commit evidence. |
| `tech_stack_drift` | Current GitHub primary-language inventory. Historical technology changes and language LOC totals are not collected. |

The stable section keys identify narrative rows; they are not promises of measurements beyond the evidence above. Missing code-maat, git-of-theseus, hercules or Repowise leaves its corresponding evidence unavailable.

For file changes, cite paths, revision counts, and the examined time span. High change frequency alone does not establish complexity or poor design. For coupling, explain the actual paired changes before judging whether the relationship is surprising. For aging, distinguish a snapshot from a survival time series. An abandoned classification does not establish that a repository is unused or safe to delete.
