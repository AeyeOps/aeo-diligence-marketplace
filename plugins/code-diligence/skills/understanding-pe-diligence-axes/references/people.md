# People axis — 5 cards

| section_key | Evidence and interpretation |
|---|---|
| `bus_factor_map` | Minimum confirmed FTEs covering 50% of git-fame LOC in production or tooling repositories. Identity aliases are combined first. Missing FTE coverage is unavailable, not zero risk. |
| `knowledge_concentration` | Top canonical contributor's share of git-fame LOC by repository. |
| `contributor_activity_timeline` | Monthly distinct canonical contributors, grouped by confirmed classification; unclassified contributors remain unknown. |
| `communication_graph` | Canonical authors linked when they change the same file in the same month. Edge weight counts shared file/month combinations. |
| `hero_dependency_register` | Files with code-maat `top_owner_pct >= 0.9`; ownership reflects historical additions, not current blamed LOC. |

Git-fame is required for the first two cards. The walker supplies activity and shared-file evidence; code-maat supplies dominant historical file ownership. Confirmed curation supplies identity, contributor, and repository classifications. An absent classification is not evidence of employment status. Set `fte_inference: false` to apply analyst curation without generating new heuristic classifications.

Narrate the measured concentration, counts, dates, and source limitations. Co-editing does not establish communication or team membership. Commit timestamps and counts do not establish individual productivity. An empty query may reflect missing tools or unreviewed curation; check Health and the underlying tables before declaring no findings.
