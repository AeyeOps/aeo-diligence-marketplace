# Skill-description review

Captured from the `claude-code-guide` agent on 2026-05-16. Drives the adversarial
case additions in [`cases.yaml`](cases.yaml) and the description tightening
applied to two of the six skills.

## Adversarial test cases (appended to cases.yaml)

The 10 `adv-*` cases probe five boundary categories:

- **(a)** warehouse-internals questions that could misroute between
  asker / interpreting-tool-output / axes
- **(b)** card- vs axis-level questions
- **(c)** "regenerate / recompute" prompts that probe refresh vs dashboard vs ingest
- **(d)** generic code-quality terms (bus factor, hotspot) that should NOT fire
- **(e)** Claude Code feature prompts that mention diligence terms incidentally

## Description weaknesses

Only two descriptions surfaced as having real boundary risk:

### interpreting-tool-output
> **Risk:** "Auto-load when reasoning" overlaps with asker (which reasons over
> warehouse queries). Targeted by `adv-warehouse-query` and `adv-missing-tool-data`.
>
> **Fix:** Rewritten to anchor on tool-interpretation boundaries with an explicit
> "not for querying the warehouse itself or writing narratives" exclusion.

### understanding-pe-diligence-axes
> **Risk:** "Reasoning about diligence insights" and "mapping a finding to a
> warehouse query" blur into interpreting-tool-output and asker. Targeted by
> `adv-card-axes-boundary` and `adv-write-card-narrative`.
>
> **Fix:** Emphasizes narrative authorship and taxonomy semantics as the primary
> gate, with an explicit "not for querying the warehouse or executing tool commands"
> exclusion.

The other four descriptions (`asking-diligence`, `building-dashboard`,
`ingesting-target`, `refreshing-target`) were reviewed and left unchanged — they
already lead with a single concrete `/code-diligence:<verb>` trigger and don't
overlap with siblings.
