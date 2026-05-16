# Test fixtures

## Synthetic target

`build_synthetic_target.sh <out>` builds a small target with six repos:

- `api`, `web` — production-ish, multiple authors, recent activity
- `contractor-tool` — single external author burst pattern
- `docs` — docs class
- `legacy-old` — abandoned (2019 commits only)
- `vendored-lib` — fork class (`.fork-of` marker)

Designed to exercise: identity aliasing (`pat@acme.com` ⇄ `pat@gmail.com`),
FTE/contractor signals (cadence + domain), repo classification heuristics.
