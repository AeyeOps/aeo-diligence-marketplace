# Renderer argument surface — `code_diligence.dashboard.render`

Entry point: `src/code_diligence/dashboard/render.py`. Invoked as a module:

    python -m code_diligence.dashboard.render <args>

## Required arguments

| Flag | Type | Purpose |
|---|---|---|
| `--warehouse` | path | Input DuckDB file, copied into an isolated temporary Observable project. |
| `--output` | path | Output directory for the built site (`dist/` is copied here, replacing any prior contents). |

## Optional arguments

| Flag | Default | Purpose |
|---|---|---|
| `--target-id` | (none) | Associates supplied curation counts with a target. All warehouse targets receive generated routes. |
| `--curation-dir` | (none) | Passed as `DILIGENCE_CURATION_DIR`. Where the curation page reads `*.yaml` from to compute "needs review" counts. |
| `--allow-working-pattern` | `false` | Writes `{"allow_working_pattern_card": true}` to `src/data/config.json`. Without this flag the same file is written with `false`. See `references/privacy-gate.md`. |

## Build behavior

1. Read the warehouse's target list through a read-only connection.
2. Run `npm ci --silent` in the template if dependencies are absent.
3. Copy template source and the warehouse into a temporary project; write its config with the target list and privacy flag.
4. Build all target routes with `npm run build --silent`.
5. After a successful build, replace the configured output directory with the generated site.

Source templates and the warehouse are not overwritten. Build failures propagate and leave the previous dashboard in place. An output path containing the input warehouse or template is rejected because replacing it would delete the input.

## Example calls

Quick-tier render with curation counts, privacy gate off:

    "$PLUGIN_ROOT/bin/run" \
      python -m code_diligence.dashboard.render \
      --warehouse ~/data/code-diligence/acme/warehouse.duckdb \
      --output ~/data/code-diligence/acme/dashboard \
      --target-id acme \
      --curation-dir ~/data/code-diligence/acme/curation

Same, with working-pattern card enabled:

    "$PLUGIN_ROOT/bin/run" \
      python -m code_diligence.dashboard.render \
      --warehouse ~/data/code-diligence/acme/warehouse.duckdb \
      --output ~/data/code-diligence/acme/dashboard \
      --target-id acme \
      --curation-dir ~/data/code-diligence/acme/curation \
      --allow-working-pattern
