# Observable template layout

Lives at: `skills/aeo-diligence-dashboard/templates/observable/` (relative to plugin root).

## Tree (tracked content only)

    observable/
    ├── .gitignore                 # excludes node_modules/, dist/, generated src/data/*.duckdb and src/data/config.json
    ├── observablehq.config.js     # site config + nav
    ├── overview.css              # shared overview layout
    ├── report.css                # Letter PDF layout
    ├── export-pdf.js             # full and section PDF generation
    ├── package.json               # @observablehq/framework + plot + echarts + duckdb-wasm + yaml
    ├── package-lock.json          # pinned deps
    └── src/
        ├── about.md
        ├── compare.md             # cross-target compare page (page template, not a separate skill)
        ├── index.md               # portfolio landing
        ├── data/
        │   ├── charts.js                # charts shared by an area page and the overview summary
        │   ├── curation-counts.txt.js   # data loader: reads YAML from DILIGENCE_CURATION_DIR
        │   ├── labels.js                # number, date, person and source-name formatting
        │   ├── overview.js              # source-labeled visual overview panels
        │   ├── metrics.js               # card queries shared by the area pages and the overview summary
        │   └── warehouse.js             # query/narrative/headlines/axisConfidence helpers over DuckDB-WASM
        └── targets/
            ├── [target].md              # overview: ownership, health, CI, development activity and Security
            └── [target]/
                ├── people.md
                ├── product.md
                ├── process.md
                ├── curation.md
                ├── repos.md
                └── health.md

## Build-time generated (gitignored)

    src/data/warehouse.duckdb      # copied by render.py into its temporary project
    src/data/activity.json         # monthly commits and code-line changes prepared by dashboard/activity.py
    src/data/security.json         # prepared period data shared by overview and Product
    src/data/config.json           # written in the temporary project with targets and the privacy flag
    node_modules/                  # npm ci
    dist/                          # observable build output, copied to --output

## What `src/data/warehouse.js` exposes

- `query(sql, params)` — async DuckDB-WASM query
- `narrative(target_id, axis, section_key)` — pulls `narratives` row
- `headlines(target_id)` — every card's title, page anchor and first narrative sentence
- `axisConfidence(target_id, axis)` — pulls `axis_confidence` row

Every page template (people.md, product.md, process.md, etc.) imports from this module.

Use `reportTable` from `src/data/tables.js` with `select: false` on display-only tables. It keeps interactive tables unchanged and includes every returned row in print mode. Enable selection only when another visible component uses the selected rows.

`Inputs.table` renders more rows as its container scrolls. Verify its complete data and scroll to the final row before reporting an omission; the initial DOM row count is only the rendered portion.

Apply `identity_map` before counting contributors in target summaries or comparisons. Label ownership measures with their file scope, especially when they include deleted files.

Size plots to the available content width and keep axis and annotation text legible alongside the page's prose. Check long labels in the rendered page after changing either size.

Keep repository scores and file details in separate tables when combining them truncates metric names or squeezes paths into narrow columns. Preserve every measure when changing the layout.

## What `src/data/config.json` exposes

A single shape:

    {"allow_working_pattern_card": true|false, "targets": ["target-id"], "display_labels": {"target-id": {"repositories": {}, "workflows": {}, "contributors": {}}}}

The optional display labels come from `dashboard.repository_labels`, `dashboard.workflow_labels` and `dashboard.contributor_labels` in the target-owned settings file beside the warehouse. Their keys are exact repository names, GitHub workflow names and canonical contributor emails. Unmapped names use the collected source labels.

Read via `FileAttachment("../../data/config.json").json()` in `targets/[target]/process.md`. See `references/privacy-gate.md` for who writes it and when.

## Adding a new card

1. Add the card markdown to the appropriate axis page (`targets/[target]/<axis>.md`). Its caption starts with `<span class="source">Source: <tool>.</span>` naming the tool that produced the evidence.
2. If the card needs SQL, query against existing warehouse tables (see `skills/aeo-diligence-axes/SKILL.md` for the axis → table map). Put a query the overview summary also reads in `metrics.js`, so both show the same number.
3. If the card needs a new warehouse table, add it to `src/code_diligence/warehouse/schema.py` and bump `SCHEMA_VERSION`, then register a migration in `migrations.py`.
4. Add a narrative section_key to `axes_taxonomy` so the narrator picks it up. Its title must match the card's heading, because overview links use the heading's anchor.
5. Update an overview panel only when the new measure belongs in that summary. Use a visible source badge and retain the detailed evidence on its area page.

`metrics.js` exposes `securityPeriods(target_id)` from the generated security data. `charts.js` exposes `securityChart(data, {width, height, invalidation})`, shared by the overview and Product. Its [input and coverage contract](security-chart.md) lives separately from presentation.

## Navigation and reports

`observablehq.config.js` owns the Dashboard return link, page PDF actions and sidebar PDF link. `export-pdf.js` composes the full report and section reports from the rendered pages, and `report.css` owns the paper layout. `charts.js` reuses its security tooltip content as printed evidence notes. See [PDF reports](pdf-reports.md).
