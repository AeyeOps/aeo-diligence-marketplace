---
name: aeo-diligence-axes
description: Reference for the People / Product / Process taxonomy, card-to-table mappings, confidence model, and narrative-writing contract (headline-first, cite warehouse numbers, state evidence gaps). Use when interpreting what a dashboard card measures, writing or updating narrative rows, understanding confidence classifications, or avoiding hallucination in PE write-ups — not for querying the warehouse or executing tool commands.
---

code-diligence organizes findings along three axes. Pick the per-axis reference for the card-to-table map; come back here for the cross-axis narration rules.

- [people](references/people.md) — 5 cards, primarily git-derived (bus factor, knowledge concentration, contributor activity, communication graph, hero register)
- [product](references/product.md) — 8 cards, code-derived plus optional security evidence (hotspots, code health, security findings, hidden coupling, code aging, burndown, abandoned areas, language inventory)
- [process](references/process.md) — 4 cards, GitHub-platform-dependent (delivery indicators, CI health, issue triage, working-pattern signals)

## Narration contract

Every dashboard card has a paired narrative row in `narratives` keyed by `(target_id, axis, section_key)`. When writing narratives:

1. **Lead with the headline finding**, not the methodology. "Three repos depend on a single committer for >70% of code knowledge" beats "Bus factor was computed using ownership_share aggregated by repo." Give each card its own finding in the first sentence: a time series should lead with its trend rather than repeat the adjacent snapshot's description.
2. **Cite a specific number from the warehouse.** For an empty result, check the underlying tables, filters, curations and collection failures. Say "data unavailable" when evidence is missing; otherwise describe that no records match the examined scope. Never fabricate a measurement or treat an empty result as proof of no risk.
3. **Name evidence gaps when confidence is low.** If `axis_confidence.confidence_class = 'low'` for the axis, explain which evidence is missing and how that limits the finding. The `missing_sources` JSON lists empty expected tables; it does not establish why they are empty.
4. **Cross-reference cards within the axis but not across axes.** "See also: knowledge concentration" is fine; reaching from People into Product muddles the partner's mental model.

5. **Write plain statements.** Apply the `humanizer` skill in embedded mode before saving a narrative. State each fact once, in the reader's words. Remove setup lines, repeated conclusions, imagined objections, and accounts of how the text was assembled. Keep source credits and limits that affect interpretation. Leave out contrast framing ("not X but Y", "X, not Y") unless both halves carry evidence or it corrects a reading the card invites. Avoid dashes, chains of semicolons, inflated words such as crucial, notably, robust, highlights, underscores and landscape, and references to "this card" or the dashboard. Read the whole paragraph for repetition and forced rhythm. Check that the edit kept every material count, name, date, comparison and caveat, and that the first sentence still makes sense on its own.

## Confidence model

The `axis_confidence` row's `confidence_class` is `high`, `medium`, or `low` based on `signal_completeness_pct`:

| Range | Class | Means |
|---|---|---|
| ≥ 80% | high | At least 80% of expected sources are present |
| 40–79% | medium | 40–79% of expected sources are present |
| < 40% | low | Fewer than 40% of expected sources are present |

A source is present when its table has rows; a GitHub table also counts when its collector ran this refresh without a current failure, because an empty result there means the feature is unused. This is a presence score, not repository coverage, result accuracy, or agreement between tools. Expected tables are defined in `src/code_diligence/narration/confidence.py`; inspect Health for missing inputs.

## Source-of-truth links

- Card-to-table-to-narrative mapping per axis: [people](references/people.md), [product](references/product.md), [process](references/process.md)
- Tool-to-table mapping (what each wrapped tool populates): `skills/aeo-diligence-tool-output/SKILL.md`
- Canonical taxonomy seeded into the warehouse at ingest: `axes_taxonomy` table, loaded from `src/code_diligence/narration/taxonomy.py`

Update the owning axis reference when a real query shows that a card or source mapping has changed.
