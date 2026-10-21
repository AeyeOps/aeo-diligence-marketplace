---
name: aeo-diligence-tool-output
description: Reference for mapping raw tool output (code-maat, hercules, git-of-theseus, git-fame, git-truck, repowise) to warehouse tables, tool-specific quirks, and cross-check rules. Use when debugging warehouse mismatches, investigating why two tools report different values for the same metric, deciding which canonical source to trust, or querying a specific warehouse table to compare per-tool entries — distinct from open-ended dashboard drill-down (asker) or writing narrative copy (axes).
---

## Quick reference — where to look first

| Question / metric | Canonical source | Cross-check | Warehouse table(s) |
|---|---|---|---|
| Per-author LOC ownership | git-fame | git-truck | `ownership_share` |
| File hotspots | code-maat (revs) + walker (revs) | repowise | `file_metrics` |
| Hidden coupling between files | code-maat | walker facts | `coupling_pairs` |
| Code aging — snapshot now | git-of-theseus | (none) | `code_age_buckets` |
| Code aging — over time | hercules | (none) | `burndown_series` |
| Bus factor | git-fame + confirmed curation | (none) | `ownership_share`, `identity_map`, `contributor_classification` |
| Dead code / "why" findings | repowise | (none) | `repowise_findings` |
| Per-commit file-author edges | walker (in-tree) | (none) | `commit_file_authors` |

Pick the per-tool reference for details:

- [code maat](references/code-maat.md) — coupling and historical ownership → `coupling_pairs`, `file_metrics`
- [hercules](references/hercules.md) — burndown matrices → `burndown_series`
- [git of theseus](references/git-of-theseus.md) — cohort survival → `code_age_buckets`
- [git fame](references/git-fame.md) — per-author LOC + commits + files → `ownership_share` (canonical)
- [git truck](references/git-truck.md) — file tree with top contributor → `ownership_share` (cross-check only)
- [repowise](references/repowise.md) — health scores and findings via the CLI adapter → `repowise_health`, `repowise_findings`
- [AWS Inspector](references/inspector.md) — findings in the target's selected scope and monthly balance → `security_reads`, `security_observations`, `security_monthly`

Plus the cross-source disagreement policy: [cross check policy](references/cross-check-policy.md).

## Quick rules

1. If a card asks "who owns this code," prefer `ownership_share` rows where `source = 'git-fame'`. Git-truck is change-volume-based and name-keyed; it measures a different quantity.
2. If a card asks "how is the codebase aging," there are two answers: `code_age_buckets` is a snapshot (git-of-theseus, quick tier); `burndown_series` is a time series (hercules, full tier). Use the time series when it's available.
3. The pipeline does not compute cross-tool disagreements automatically; compare the records and units before interpreting a difference. See [cross check policy](references/cross-check-policy.md).

## Where the per-tool wrappers live

Source code: `src/code_diligence/tools/<tool>.py`. Read the selected module and its orchestration call site for the exact run and persistence signatures. Both are exercised by tests under `tests/tools/`.

Update the owning tool reference when an observed output format or invocation changes.
