# People axis — 5 cards

Primarily git-derived. Renders even on quick-tier ingest. `axis_confidence` is `high` when the walker plus git-fame have populated the warehouse.

## Card map

| section_key | Card | Backed by | Primary source | Render site |
|---|---|---|---|---|
| `bus_factor_map` | Bus factor map | `commits_fact` + `ownership_share` + `repo_classification` | walker + git-fame + curation | `skills/building-dashboard/templates/observable/src/targets/[target]/people.md` |
| `knowledge_concentration` | Knowledge concentration heatmap | `ownership_share` filtered to `source = 'git-fame'` | git-fame | same |
| `contributor_activity_timeline` | Contributor activity timeline | `commits_fact` × `contributor_classification` (FTE vs. contractor vs. bot) | walker + curation | same |
| `communication_graph` | Communication graph | `commit_file_authors` joined to itself by `(repo_id, month, file_path)` with `author_email_a < author_email_b` | walker (per-file edges) | same |
| `hero_dependency_register` | Hero / dependency register | `file_metrics` filtered to `top_owner_pct >= 0.9` | walker | same |

## Source dependencies

| Source | Without it | Effect on People confidence |
|---|---|---|
| git walker | nothing renders | `low` (axis empty) |
| git-fame | `knowledge_concentration` empty, `bus_factor_map` weaker (no LOC weighting) | `medium` |
| curation YAMLs (`repo_classification`, `contributor_classification`) | `bus_factor_map` and `contributor_activity_timeline` lose filtering by repo class / contributor class | `medium` |

## Narration patterns per card

- **bus_factor_map** — Lead with the count of repos at bus factor ≤ 2. Name the worst offender (lowest bus factor + production class). If every production repo has bus factor ≥ 3, say so plainly.
- **knowledge_concentration** — Lead with the count of repos where top-1 author owns ≥ 60% of LOC. Avoid the word "siloed" — partners want concrete counts.
- **contributor_activity_timeline** — Lead with the trend over the last 12 months: growing, flat, or shrinking active-contributor count. Distinguish FTEs from contractors when both bands are visible.
- **communication_graph** — Lead with the count of cross-team co-editing pairs (authors from different domain groups). If the graph is "many small clusters with no bridges," that's a finding — repos are siloed by team.
- **hero_dependency_register** — Lead with the count of files where one author owns ≥ 90%. Cite two or three example `repo/path` if the list is short.

## Common confusions

- "Bus factor" is a noun phrase here, not the loaded "number of people who can be hit by a bus before the project dies." We report it as **minimum FTEs to cover 50% of code knowledge**, computed from `ownership_share`.
- The communication graph uses **monthly co-edit windows per file**, not commit-level coincidence. That's why it's backed by `commit_file_authors` since v1.1.0 — the older `commits_fact`-self-join placeholder over-counted because it didn't constrain on shared file.
