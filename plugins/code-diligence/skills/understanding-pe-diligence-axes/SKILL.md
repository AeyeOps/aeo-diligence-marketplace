---
name: understanding-pe-diligence-axes
description: Reference for the People / Product / Process taxonomy, card-to-table mappings, confidence model, and narrative-writing contract (headline-first, cite warehouse numbers, hedge on low confidence). Use when interpreting what a dashboard card measures, writing or updating narrative rows, understanding confidence classifications, or avoiding hallucination in PE write-ups — not for querying the warehouse or executing tool commands.
---

code-diligence organizes findings along three axes. Pick the per-axis reference for the card-to-table map; come back here for the cross-axis narration rules.

- [people](references/people.md) — 5 cards, primarily git-derived (bus factor, knowledge concentration, contributor activity, communication graph, hero register)
- [product](references/product.md) — 6 cards, code-derived (hotspots, hidden coupling, code aging, burndown, abandoned areas, language inventory)
- [process](references/process.md) — 5 cards, GitHub-platform-dependent (delivery indicators, review discipline, CI health, issue triage, working-pattern signals)

## Narration contract

Every dashboard card has a paired narrative row in `narratives` keyed by `(target_id, axis, section_key)`. When writing narratives:

1. **Lead with the headline finding**, not the methodology. "Three repos depend on a single committer for >70% of code knowledge" beats "Bus factor was computed using ownership_share aggregated by repo."
2. **Cite a specific number from the warehouse.** For an empty result, check the underlying tables, filters, curations and collection failures. Say "data unavailable" when evidence is missing; otherwise describe that no records match the examined scope. Never fabricate a measurement or treat an empty result as proof of no risk.
3. **Hedge when confidence is low.** If `axis_confidence.confidence_class = 'low'` for the axis, prefix the headline with "Limited signal:" and explain the evidence gap. The `missing_sources` JSON lists empty expected tables; it does not establish why they are empty.
4. **Cross-reference cards within the axis but not across axes.** "See also: knowledge concentration heatmap" is fine; reaching from People into Product muddles the partner's mental model.

## Confidence model

The `axis_confidence` row's `confidence_class` is `high`, `medium`, or `low` based on `signal_completeness_pct`:

| Range | Class | Means |
|---|---|---|
| ≥ 80% | high | At least 80% of expected tables have rows |
| 40–79% | medium | 40–79% of expected tables have rows |
| < 40% | low | Fewer than 40% of expected tables have rows |

This is a table-presence score, not repository coverage, result accuracy, or agreement between tools. Expected tables are defined in `src/code_diligence/narration/confidence.py`; inspect Health for missing inputs.

## Source-of-truth links

- Card-to-table-to-narrative mapping per axis: [people](references/people.md), [product](references/product.md), [process](references/process.md)
- Tool-to-table mapping (what each wrapped tool populates): `skills/interpreting-tool-output/SKILL.md`
- Canonical taxonomy seeded into the warehouse at ingest: `axes_taxonomy` table, loaded from `src/code_diligence/narration/taxonomy.py`

Update the owning axis reference when a real query shows that a card or source mapping has changed.
