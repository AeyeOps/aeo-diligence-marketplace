---
name: aeo-diligence-dashboard
description: Build or rebuild the Observable dashboard from an existing code-diligence warehouse, including after curation or narrative changes. Does not refresh source repositories.
allowed-tools: Bash, Read
---

# Build a diligence dashboard

In Claude Code invoke `/code-diligence:aeo-diligence-dashboard` from the plugin or `/aeo-diligence-dashboard` as a standalone skill; in Codex invoke `$aeo-diligence-dashboard`.

Read the target's `diligence.local.md` in its target folder. The `aeo-diligence-ingest` skill's step 1 locates the folder and step 3 resolves `$PLUGIN_ROOT`. Pass all three paths and the target ID:

```sh
"$PLUGIN_ROOT/bin/run" python -m code_diligence.dashboard.render \
  --warehouse "$WAREHOUSE_PATH" --output "$OUTPUT_PATH" \
  --target-id "$TARGET_ID" --curation-dir "$CURATION_DIR"
```

The overview presents code ownership, paired code-health scores with Repowise grades, CI results, monthly commits beside code lines added and removed, and the existing Security chart. Each panel names its source. CI results and Development activity share equal width. Keep detailed findings on their existing area pages.

Target names, display labels, contributor decisions and supplied Security history belong in the target repository. Read optional `dashboard.repository_labels`, `dashboard.workflow_labels` and `dashboard.contributor_labels` from `diligence.local.md` beside the warehouse; the renderer applies them without changing source identifiers. Contributor labels use canonical email keys and appear wherever the dashboard names a person. Keep generated dashboards, PDFs, warehouses and cloned repositories out of version control.

When contributor display labels change, update those names in existing target narratives before rebuilding. Preserve their measured facts and findings. Pass the same labels in narration context on future ingest and refresh runs.

Pass `--allow-working-pattern` only when `heuristics.allow_working_pattern_card` is true. The renderer replaces its configured output directory, so use `dashboard.output_path` rather than a source or repository directory.

Security belongs to Product. Follow the [security chart contract](references/security-chart.md) for its interval, range, supplied counts and partial evidence. When `dashboard.security_chart_path` is set, resolve it against the settings folder and pass `--security-chart "$SECURITY_CHART_PATH"`. Use the same input for preparation, narration and rendering. Check the existing Security narrative against those prepared counts and refresh it when the measurement, scope or period changes. Without an input file, the chart uses monthly periods across the target's recorded Inspector history.

When bringing an existing chart into the dashboard, carry its complete data through the chart generator before rebuilding. Save supplied counts, estimates and starting points in the target's chart input and record that path in its settings. Compare every displayed period, movement total and backlog point with the existing chart; a shorter native snapshot history does not replace available historical data.

Before reporting a build, check the overview summary against the captured warehouse records and source artifacts from the same collection. Keep the recorded revision, time window, file scope and denominator. A rebuild does not require live repository or GitHub access. Reconcile against live sources during collection or an explicitly requested refresh, preserving their collection boundaries. Each summary number names its scope and the tool that produced it.

When reviewing the output, visit every generated page and section, including tables below the fold, chart interactions, empty states and links. Compare displayed numbers and prose with the underlying records at the collection date, keeping each measure's scope and denominator. Apply the `humanizer` skill to narratives and visible template prose; preserve source credits and evidence limits. Read overview headlines separately from their full paragraphs. Check the rendered pages for clipped values, overlapping labels, unreadable columns and misleading omissions. Fix each confirmed issue in its source template, query or narration instructions, rebuild, and revisit the affected pages.

On success, give the output path and `python -m http.server --directory "$OUTPUT_PATH"` preview command. Every build includes a US Letter full PDF per target and a PDF for each section. The full report places the dashboard immediately after its cover. Check that the target overview fits its intended page without discarding data or shrinking text to force a fit. The page action bar and sidebar link back to the target Dashboard and offer PDF downloads. PDF generation uses an isolated headless Chromium; it never connects to an operator browser. Use the installed Chromium or set `DILIGENCE_CHROMIUM_PATH`; otherwise install the matching browser once with `npx playwright install chromium` from the Observable template directory. When end-to-end validation is requested, prefer a browser automation tool that is already installed, such as `agent-browser`; if none is, work with the operator to install one before validating. If Health or a card exposes a confirmed collection or narration gap, follow the coverage procedure in the `aeo-diligence-ingest` skill's `references/tool-prerequisites.md`: explain the missing result and the remedy, then carry out authorized recovery or establish whether the user accepts reduced coverage. Building alone does not recover missing evidence. On failure, report the command's error; do not claim that the prior dashboard is current.

- [PDF reports](references/pdf-reports.md): standard navigation, full and section downloads, rendering and visual checks.
- [Renderer arguments](references/render-args.md): inputs, output replacement and build behavior.
- [Privacy setting](references/privacy-gate.md): the existing opt-in contract.
- [Template layout](references/template-layout.md): page and asset ownership.
- [Security chart](references/security-chart.md): attributes, supported subsets, period conversion, narration and review.

Update the owning reference when an observed runtime change makes it inaccurate.
