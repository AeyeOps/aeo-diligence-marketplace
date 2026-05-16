# Privacy gate — working-pattern card

The working-pattern card in `process.md` aggregates commit timestamps to the repo level (day-of-week × hour heatmap). Even though no individual identity surfaces in the rendered chart, the underlying signal is sensitive in privacy-strict contexts (employment law in some jurisdictions; works-council agreements; ethical review for portfolio companies with hourly workers).

## The contract

The renderer always writes `<plugin>/skills/building-dashboard/templates/observable/src/data/config.json` with shape:

    {"allow_working_pattern_card": true|false}

Default is `false` — meaning the dashboard renders an "opt-in notice" in place of the heatmap. The flag flips true only when `--allow-working-pattern` is passed to `code_diligence.dashboard.render`, which itself is gated on the target's `heuristics.allow_working_pattern_card: true` setting.

## How to decide

| Context | Default | Rationale |
|---|---|---|
| New target, unknown jurisdiction | `false` | Privacy-by-default; analyst can opt in once cleared |
| US-based portfolio with explicit diligence-scope letter | `false` until letter cited in settings | Diligence scope sometimes excludes "work-time analysis" |
| EU portfolio | keep `false` | Strong default; works-council notice often required |
| Open-source-only analysis with public commits | `true` after user toggle | Commit times are public anyway |

## What "off" looks like

When the flag is false, `process.md` displays:

> Working pattern signals disabled — set `allow_working_pattern_card: true` in settings to enable.

No SQL is executed for the heatmap; no narrative is rendered. The rest of the Process axis is unaffected.

## Cross-references

- Setting that controls it: `settings/diligence.example.local.md` under `heuristics.allow_working_pattern_card`
- Renderer flag: `src/code_diligence/dashboard/render.py` (`--allow-working-pattern`)
- Conditional render site: `skills/building-dashboard/templates/observable/src/targets/[target]/process.md`
- Pydantic schema: `src/code_diligence/settings/schema.py` (`Heuristics.allow_working_pattern_card`, defaults to `False`)
