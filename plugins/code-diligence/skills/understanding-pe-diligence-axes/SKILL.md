---
name: understanding-pe-diligence-axes
description: Reference for the People / Product / Process taxonomy used in code-diligence dashboards — what each axis covers, which warehouse tables back each card, which tools populate those tables, and how to write narratives for each card without hallucinating numbers. Auto-load when reasoning about diligence insights, mapping a finding to a warehouse query, or generating narratives.
---

code-diligence organizes findings along three axes. Pick the per-axis reference for the card-to-table map; come back here for the cross-axis narration rules.

- `references/people.md` — 5 cards, primarily git-derived (bus factor, knowledge concentration, contributor activity, communication graph, hero register)
- `references/product.md` — 6 cards, code-derived (hotspots, hidden coupling, code aging, burndown, abandoned areas, tech-stack drift)
- `references/process.md` — 5 cards, GitHub-platform-dependent (DORA, review discipline, CI health, issue triage, working-pattern signals)

## Narration contract

Every dashboard card has a paired narrative row in `narratives` keyed by `(target_id, axis, section_key)`. When writing narratives:

1. **Lead with the headline finding**, not the methodology. "Three repos depend on a single committer for >70% of code knowledge" beats "Bus factor was computed using ownership_share aggregated by repo."
2. **Cite a specific number from the warehouse.** If the underlying query returns zero rows, say "data unavailable" — never fabricate.
3. **Hedge when confidence is low.** If `axis_confidence.confidence_class = 'low'` for the axis, prefix the headline with "Limited signal:" and explain which sources were missing (`missing_sources` JSON in the same row).
4. **Cross-reference cards within the axis but not across axes.** "See also: knowledge concentration heatmap" is fine; reaching from People into Product muddles the partner's mental model.

## Confidence model

The `axis_confidence` row's `confidence_class` is `high`, `medium`, or `low` based on `signal_completeness_pct`:

| Range | Class | Means |
|---|---|---|
| ≥ 80% | high | Every primary source for this axis populated the warehouse |
| 50–79% | medium | At least one secondary source missing; cards render with caveats |
| < 50% | low | Primary source missing or unusable; the axis is mostly empty |

Each axis has its own primary/secondary source list — see the per-axis references.

## Source-of-truth links

- Card-to-table-to-narrative mapping per axis: `references/people.md`, `references/product.md`, `references/process.md`
- Tool-to-table mapping (what each wrapped tool populates): `skills/interpreting-tool-output/SKILL.md`
- Canonical taxonomy seeded into the warehouse at ingest: `axes_taxonomy` table, loaded from `src/code_diligence/narration/taxonomy.py`
