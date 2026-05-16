# Cross-source disagreement policy

When two tools populate the same logical metric, the warehouse stores both with a `source` discriminator. Disagreements are not errors — they are signals.

## How disagreements are surfaced

The pipeline computes a sanity diff at the end of stage 4 (cheap tools) and stage 6 (expensive tools). Diffs that cross a configurable threshold get written as `tool_failures` rows of class `data_sanity`:

| Logical metric | Sources | Threshold |
|---|---|---|
| Ownership (per repo, top author %) | git-fame, git-truck, repowise | absolute difference > 20 percentage points |
| Hotspots (top-10 files by composite score) | code-maat, repowise | symmetric set difference > 4 files |
| Bus factor (per repo) | code-maat, repowise | difference > 1 |
| Coupling (top-20 pairs) | code-maat, hercules | symmetric set difference > 8 pairs |

These rows do not block the pipeline. The dashboard's Health tab reads `tool_failures WHERE class='data_sanity'` and renders them as advisories.

## Dashboard preference per metric

When multiple sources exist and no override is set, the dashboard uses these defaults:

| Card | Preferred source | Why |
|---|---|---|
| `knowledge_concentration`, `hero_dependency_register` | git-fame | Email-keyed, blame-based, canonical |
| `hidden_coupling_matrix` | code-maat | Most mature coupling heuristic |
| `code_aging_chart` | git-of-theseus | Snapshot semantics match the card |
| `burndown_over_time` | hercules | Time-series semantics match the card |
| `bus_factor_map` | code-maat | Cross-validated with repowise on Health tab |
| `dead_code` evidence in `abandoned_area_register` | repowise | Only source that emits dead-code findings |

## What to do when sources disagree

1. Open the Health tab and read the `data_sanity` advisory.
2. Identify which dimension the disagreement is on (file set, author identity, percentage).
3. Most common root cause: **identity merging gaps**. Check `storage.curation_dir/identity-merges.yaml` — a single contributor showing as two emails will skew per-author metrics in opposite directions across tools.
4. Second most common: **generated-code differences**. git-fame respects `.gitattributes` `linguist-generated`; code-maat does not. A large generated directory will pull top-owner percentages apart.
5. Third most common: **bot accounts**. If `dependabot[bot]` or similar is not classified as a bot in `contributor_classification`, its commits will get attributed to whichever tool's heuristic picks them up.

## Override mechanism

There is no per-target source override yet. If you must force a specific source for a card, edit the dashboard SQL in `skills/building-dashboard/templates/observable/src/targets/[target]/<axis>.md` to add a `WHERE source = '...'` clause. The change ships with the dashboard build; it does not modify the warehouse.
