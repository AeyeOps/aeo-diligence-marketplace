# Standard dashboard reports

Every dashboard build produces PDFs from the same warehouse and narratives as its interactive pages. This is part of the dashboard skill, including builds invoked by ingest and refresh.

- The Dashboard link in each page action bar returns to the target overview. The target sidebar calls that entry Dashboard.
- The target action bar and sidebar offer Download full PDF.
- Each target section offers Download section PDF, limited to that area.
- Files live at `reports/<target>/report.pdf` and `reports/<target>/<section>.pdf`. The full report includes Dashboard, People, Product, Process, Repositories, Curation, Evidence health and Methodology.

## Rendering

The renderer runs `export-pdf.js` after Observable finishes and before replacing the configured output. It serves the build on loopback, visits one source page at a time in an isolated headless Chromium, waits for Observable output and fonts, and composes searchable, tagged PDFs with vector charts. `overview.css` supplies the shared visual dashboard layout. `report.css` owns the US Letter paper layout, half-inch margins, cover, linked contents, headings, tables and pagination. The dashboard follows the cover; its print layout preserves the paired panels and equal-width CI and Development activity sections. Source badges and source captions remain highlighted in PDF output. Below “In this report,” the cover gives one line per tool explaining the evidence it provides from a diligence perspective. The target data refresh date appears at the right of every page footer; it is not the PDF generation date.

Set `DILIGENCE_CHROMIUM_PATH` to choose an executable. The renderer otherwise detects Chromium or Google Chrome on PATH. When neither is installed, use Playwright's matching browser: run `npx playwright install chromium` once from `templates/observable`. Do not attach to the user's browser for a build.

The exporter captures the dashboard with a 1040-pixel content width and scales its original Security SVG proportionally for print. The fixed content width keeps the browser sidebar from changing the chart's aspect ratio. It captures the other sections with `?print`, which makes `reportTable` render every row returned by the page's existing query, preserving its sorting and formatters. It does not expand query limits. The exporter removes scrolling and selection controls. The Product section includes Security tooltip evidence as printed notes, including source, period coverage, estimates and differences.

## Review

Check the Dashboard return link, the sidebar full PDF link, and each primary page's section download in a real browser. Verify US Letter dimensions and inspect dashboard page 2 against the interactive overview. Review the PDFs as pages, including the cover, contents, tables spanning pages, chart labels, source captions and the final page. Check that the full report includes every area and that section reports exclude other areas. Long tables must retain the final row. A completed build alone does not establish visual quality.
