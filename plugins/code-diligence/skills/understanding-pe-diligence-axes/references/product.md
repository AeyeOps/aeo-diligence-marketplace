# Product axis — 6 cards

Code-derived. The first four cards render on quick-tier ingest; `burndown_over_time` and the most precise `hidden_coupling_matrix` require full-tier (hercules + code-maat).

## Card map

| section_key | Card | Backed by | Primary source | Tier |
|---|---|---|---|---|
| `hotspot_map` | Hotspot map | `file_metrics` (revisions × complexity_proxy) filtered by `repo_classification` | walker + curation (+ repowise on full tier) | quick |
| `hidden_coupling_matrix` | Hidden coupling matrix | `coupling_pairs` | code-maat (full); cross-check with hercules | full preferred |
| `code_aging_chart` | Code aging chart | `code_age_buckets` | git-of-theseus | quick |
| `burndown_over_time` | Burndown over time | `burndown_series` | hercules | full only |
| `abandoned_area_register` | Abandoned area register | `repos` + `repo_classification (class='abandoned')` (+ repowise `dead_code` findings on full) | curation | quick |
| `tech_stack_drift` | Tech-stack drift | `repos.languages` over time, derived from `commits_fact` per language file extension | walker | quick |

## Source dependencies

| Source | Without it | Effect on Product confidence |
|---|---|---|
| git walker | nothing renders | `low` |
| git-of-theseus | `code_aging_chart` empty | `medium` |
| code-maat | `hidden_coupling_matrix` weak (no `coupling_pairs` from this source); falls back to repowise findings | `medium` |
| hercules | `burndown_over_time` empty | `medium` (acceptable on quick tier) |
| repowise | `dead_code` not surfaced in `abandoned_area_register` | `medium` |

## Narration patterns per card

- **hotspot_map** — Lead with the top three hotspot files in production-class repos. Cite `revisions × complexity_proxy` score. Hotspots in `tooling` class are not the same problem; mention separately if interesting.
- **hidden_coupling_matrix** — Lead with the strongest unexpected pair (high lift, low support implies a non-obvious coupling). Avoid pairs in the same directory — those are usually intentional.
- **code_aging_chart** — Lead with the share of LOC older than 5 years and the share newer than 1 year. Both are legitimate findings depending on the thesis: old-stable is a moat, old-stagnant is risk.
- **burndown_over_time** — Lead with the half-life: at what year did total surviving LOC drop below 50% of its peak? If the codebase is monotonically growing, say so — burndown still shows cohort survival per year.
- **abandoned_area_register** — Lead with the count of repos classified abandoned and the most recently abandoned one. If any abandoned repo has open PRs or recent issues, flag that — abandonment is a curation guess and recent activity may contradict it.
- **tech_stack_drift** — Lead with the dominant language by current LOC and the most recently introduced major language. Drift here is interesting when it implies an in-flight rewrite or a polyglot service mesh.

## Common confusions

- `complexity_proxy` is **not** cyclomatic complexity. It's a heuristic blend of file size, depth in directory tree, and revision velocity. Document it as "complexity proxy" when narrating; don't claim McCabe.
- "Hotspot" requires both axes: high revision count **and** high complexity proxy. A file revised 200 times but trivial is not a hotspot.
- `abandoned` does not mean "deletable." It means "no commits in the last `heuristics.abandoned_threshold_days` days." The curation step's role is exactly to let the analyst reclassify false-positives.
