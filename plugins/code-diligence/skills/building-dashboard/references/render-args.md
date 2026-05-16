# Renderer argument surface — `code_diligence.dashboard.render`

Entry point: `src/code_diligence/dashboard/render.py`. Invoked as a module:

    python -m code_diligence.dashboard.render <args>

## Required arguments

| Flag | Type | Purpose |
|---|---|---|
| `--warehouse` | path | Input DuckDB file. Copied verbatim into the Observable template at `skills/building-dashboard/templates/observable/src/data/warehouse.duckdb`. |
| `--output` | path | Output directory for the built site (`dist/` is copied here, replacing any prior contents). |

## Optional arguments

| Flag | Default | Purpose |
|---|---|---|
| `--target-id` | (none) | Passed to Observable as `DILIGENCE_TARGET` env var. Drives parameterized `[target]` routes. |
| `--curation-dir` | (none) | Passed as `DILIGENCE_CURATION_DIR`. Where the curation page reads `*.yaml` from to compute "needs review" counts. |
| `--allow-working-pattern` | `false` | Writes `{"allow_working_pattern_card": true}` to `src/data/config.json`. Without this flag the same file is written with `false`. See `references/privacy-gate.md`. |

## Side effects

1. Runs `npm install --silent` in the template if `node_modules/` is absent.
2. Writes `src/data/warehouse.duckdb` (overwrite).
3. Writes `src/data/config.json` (overwrite — always written, regardless of flag value).
4. Runs `npm run build --silent` with the env vars above.
5. Removes any existing `<output_path>` and copies `dist/` to it.

Steps 2 and 3 are ephemeral build artifacts and are gitignored in the template's `.gitignore`.

## Failure modes

- `npm install` failure → propagates `CalledProcessError`; the renderer does not retry.
- `npm run build` failure → propagates; usually means an Observable page template has a syntax error, or a SQL query in `*.md` references a table the warehouse doesn't have.
- Missing input warehouse → `shutil.copy` raises `FileNotFoundError`.

## Example calls

Quick-tier render with curation counts, privacy gate off:

    uv run --directory ${CLAUDE_PLUGIN_ROOT} \
      python -m code_diligence.dashboard.render \
      --warehouse ~/data/code-diligence/acme.duckdb \
      --output ~/data/code-diligence/dashboard/acme \
      --target-id acme \
      --curation-dir ~/data/code-diligence/acme/curation

Same, with working-pattern card enabled:

    uv run --directory ${CLAUDE_PLUGIN_ROOT} \
      python -m code_diligence.dashboard.render \
      --warehouse ~/data/code-diligence/acme.duckdb \
      --output ~/data/code-diligence/dashboard/acme \
      --target-id acme \
      --curation-dir ~/data/code-diligence/acme/curation \
      --allow-working-pattern
