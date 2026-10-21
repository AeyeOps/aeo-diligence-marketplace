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
| `--security-chart` | (none) | Repeatable path to a [security chart input](security-chart.md), one per target. Overrides that target's interval, range or supplied observations. Other targets use recorded history with monthly periods. |

## Build behavior

1. Read the warehouse's target list through a read-only connection.
2. Run `npm ci --silent` in the template if dependencies are absent.
3. Copy template source and the warehouse into a temporary project; migrate the warehouse schema and update taxonomy in that copy, prepare `src/data/security.json` and `src/data/activity.json`, and write config with the target list, privacy flag and target-owned display labels.
4. Build all target routes with `npm run build --silent`.
5. Render full and section PDFs in an isolated headless Chromium.
6. After successful site and PDF generation, replace the configured output directory with both outputs.

When `diligence.local.md` exists beside the warehouse, the renderer reads its repository, workflow and contributor display labels for that settings file's target. Other targets retain their source names. Monthly activity is derived from collected Git author dates; added and removed lines use the same filename selection as the pinned git-of-theseus/Pygments dependencies. The renderer streams grouped file changes and does not rescan repositories.

Source templates and the warehouse are not overwritten. Build failures propagate and leave the previous dashboard in place. An output path containing the input warehouse or template is rejected because replacing it would delete the input.

The command reports peak resident memory in MiB for the renderer or its largest child process. This is not the simultaneous total of all child processes.

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

## Standard PDF output

After the Observable build, `export-pdf.js` renders each target sequentially in headless Chromium. It writes `reports/<target>/report.pdf` and section PDFs before the output directory is replaced. A PDF failure fails the build and retains the previous output. `DILIGENCE_CHROMIUM_PATH` selects the browser executable; otherwise the renderer detects Chromium or Google Chrome on PATH, then uses Playwright's installed browser. See [PDF reports](pdf-reports.md).
