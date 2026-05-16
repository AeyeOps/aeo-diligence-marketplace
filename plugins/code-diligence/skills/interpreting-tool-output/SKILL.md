---
name: interpreting-tool-output
description: Reference for mapping raw tool output (code-maat, hercules, git-of-theseus, git-fame, git-truck, repowise) to warehouse tables, tool-specific quirks, and cross-check rules. Use when debugging warehouse mismatches, investigating why two tools report different values for the same metric, deciding which canonical source to trust, or querying a specific warehouse table to compare per-tool entries — distinct from open-ended dashboard drill-down (asker) or writing narrative copy (axes).
---

## Quick reference — where to look first

| Question / metric | Canonical source | Cross-check | Warehouse table(s) |
|---|---|---|---|
| Per-author LOC ownership | git-fame | git-truck | `ownership_share` |
| File hotspots | code-maat (revs) + walker (revs) | repowise | `file_metrics` |
| Hidden coupling between files | code-maat | hercules | `coupling_pairs` |
| Code aging — snapshot now | git-of-theseus | (none) | `code_age_buckets` |
| Code aging — over time | hercules | (none) | `burndown_series` |
| Bus factor | code-maat | repowise | `bus_factor` (computed downstream) |
| Dead code / "why" findings | repowise | (none) | `repowise_findings` |
| Per-commit file-author edges | walker (in-tree) | (none) | `commit_file_authors` |

Pick the per-tool reference for details:

- `references/code-maat.md` — coupling matrices, soc, ownership → `coupling_pairs`, `bus_factor`, `file_metrics`
- `references/hercules.md` — burndown matrices → `burndown_series`, supplementary `coupling_pairs`
- `references/git-of-theseus.md` — cohort survival → `code_age_buckets`
- `references/git-fame.md` — per-author LOC + commits + files → `ownership_share` (canonical)
- `references/git-truck.md` — file tree with top contributor → `ownership_share` (cross-check only)
- `references/repowise.md` — typed findings via MCP → `repowise_findings`, augments `bus_factor` and `file_metrics`

Plus the cross-source disagreement policy: `references/cross-check-policy.md`.

## Quick rules

1. If a card asks "who owns this code," prefer `ownership_share` rows where `source = 'git-fame'`. Git-truck is byte-size-proxied and name-based, not email-based — keep it for the "Health" cross-check tab only.
2. If a card asks "how is the codebase aging," there are two answers: `code_age_buckets` is a snapshot (git-of-theseus, quick tier); `burndown_series` is a time series (hercules, full tier). Use the time series when it's available.
3. Disagreements between tools writing to the same logical metric are not bugs — they are recorded as `tool_failures` rows of class `data_sanity` and shown on the dashboard's Health tab. See `references/cross-check-policy.md`.

## Where the per-tool wrappers live

Source code: `src/code_diligence/tools/<tool>.py`. Each module exposes `run_<tool>(repo_path)` and `persist_<tool>(conn, repo_id, records)`. Both are exercised by tests under `tests/tools/`.
