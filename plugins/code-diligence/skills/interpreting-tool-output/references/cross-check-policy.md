# Comparing tool evidence

The warehouse preserves source-specific results. The pipeline does not compute cross-tool disagreements or insert `data_sanity` advisories automatically. Health shows recorded tool failures, completeness, and tool versions.

## Source selection

| Evidence | Source used by the dashboard |
|---|---|
| Surviving LOC ownership and bus factor | git-fame, with confirmed identity and contributor classifications |
| File revision counts | walker, updated by code-maat when run |
| Dominant historical file contributor | code-maat entity ownership |
| Hidden coupling | code-maat pairs with counts, support and lift computed from walker facts |
| Current code vintage | git-of-theseus |
| Code survival over time | hercules |
| Raw supplemental findings | repowise; queried separately, not merged into cards |

Before comparing numbers, compare their units, file set, time window, and identity handling. Git-fame measures surviving blamed lines; git-truck measures historical change volume under display names. Those numbers are not interchangeable. A difference alone does not establish that either tool failed.

Use the tool references to trace the value into its warehouse column, then query the actual records. Report the scope and explanation of a disagreement with evidence. There is no configurable source-override mechanism.
