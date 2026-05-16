# Observable template layout

Lives at: `skills/building-dashboard/templates/observable/` (relative to plugin root).

## Tree (tracked content only)

    observable/
    ├── .gitignore                 # excludes node_modules/, dist/, generated src/data/*.duckdb and src/data/config.json
    ├── observablehq.config.js     # site config + nav
    ├── package.json               # @observablehq/framework + plot + duckdb-wasm + yaml
    ├── package-lock.json          # pinned deps
    └── src/
        ├── about.md
        ├── compare.md             # cross-target compare page (page template, not a separate skill)
        ├── curation.md            # per-target curation status (page template, not a separate skill)
        ├── index.md               # portfolio landing
        ├── data/
        │   ├── curation-counts.txt.js   # data loader: reads YAML from DILIGENCE_CURATION_DIR
        │   └── warehouse.js             # query/narrative/axisConfidence helpers over DuckDB-WASM
        └── targets/
            ├── [target].md              # parameterized target landing
            └── [target]/
                ├── people.md
                ├── product.md
                ├── process.md
                ├── curation.md
                └── compare.md

## Build-time generated (gitignored)

    src/data/warehouse.duckdb      # written by render.py from --warehouse
    src/data/config.json           # written by render.py with {allow_working_pattern_card: bool}
    node_modules/                  # npm install
    dist/                          # observable build output, copied to --output

## What `src/data/warehouse.js` exposes

- `query(sql, params)` — async DuckDB-WASM query
- `narrative(target_id, axis, section_key)` — pulls `narratives` row
- `axisConfidence(target_id, axis)` — pulls `axis_confidence` row

Every page template (people.md, product.md, process.md, etc.) imports from this module.

## What `src/data/config.json` exposes

A single shape:

    {"allow_working_pattern_card": true|false}

Read via `FileAttachment("../../data/config.json").json()` in `targets/[target]/process.md`. See `references/privacy-gate.md` for who writes it and when.

## Adding a new card

1. Add the card markdown to the appropriate axis page (`targets/[target]/<axis>.md`).
2. If the card needs SQL, query against existing warehouse tables (see `skills/understanding-pe-diligence-axes/SKILL.md` for the axis → table map).
3. If the card needs a new warehouse table, add it to `src/code_diligence/warehouse/schema.py` and bump `SCHEMA_VERSION`, then register a migration in `migrations.py`.
4. Add a narrative section_key to `axes_taxonomy` so the narrator picks it up.
