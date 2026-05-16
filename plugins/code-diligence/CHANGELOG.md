# Changelog

All notable changes to the `code-diligence` plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.2] — 2026-05-16

### Added
- `scripts/skill_eval/` — a non-interactive trigger-accuracy harness for the six skill descriptions. One `claude -p --disable-slash-commands` call per run; default judge model is Haiku 4.5. Includes 21 happy-path + 10 adversarial test cases probing boundary risks between sibling skills.

### Changed
- Tightened five skill descriptions based on harness output and a `claude-code-guide` agent review (`scripts/skill_eval/review.md`):
  - `asking-diligence` — adds an "open-ended drill-down" framing and an explicit "not for which-tool-fed-which-column" exclusion that previously bled into `interpreting-tool-output`'s territory.
  - `building-dashboard` — unchanged.
  - `ingesting-target` — now states "initial setup for a new target (no warehouse exists yet)" and points already-ingested workflows at `refreshing-target`.
  - `interpreting-tool-output` — leads with "Reference for mapping…" and lists explicit use cases (debugging mismatches, comparing per-tool entries, source-of-truth decisions); excludes open-ended drill-down and narrative writing.
  - `refreshing-target` — explicit "warehouse already exists" gate and adds "recompute / rerun / update" as natural-language triggers.
  - `understanding-pe-diligence-axes` — emphasizes narrative authorship + taxonomy semantics + confidence model; explicit exclusion of warehouse queries and tool commands.
- Harness aggregate accuracy: 31/31 across 5 consecutive runs after the tightening (baseline was 29/31).

## [1.1.1] — 2026-05-16

### Fixed
- `plugin.json` `repository` field reshaped from `{type, url}` object to a plain string, the form Claude Code's manifest schema accepts. `claude plugin install code-diligence@aeo-diligence` previously rejected the manifest; the install now succeeds end-to-end.

## [1.1.0] — 2026-05-15

Initial public release.

### Added
- DuckDB-backed multi-target warehouse with full schema and migrations.
- `code-diligence ingest <target> [--quick|--full]` pipeline: clone, walk, run wrapped analyzers, curate, optionally hit the GitHub platform API, narrate, snapshot tool versions. Idempotent at every stage.
- Wrappers for `git-fame`, `git-of-theseus`, `git-truck`, `hercules`, `code-maat`, and `repowise`. Missing tools degrade gracefully to "data unavailable" rather than fail the run.
- Heuristics: identity merging, FTE classification, repo classification.
- Curation YAMLs with analyst-confirmed / needs-review / do-not-merge buckets that survive every rerun.
- Observable dashboard: parameterized `[target]` route covering 16 cards across People (5), Product (6), and Process (5) axes, plus cross-target compare, curation review, and Health tabs.
- Narrator agent (per-card prose) and asker agent (read-only conversational drill-down with explicit tool allowlist).
- MCP server (`diligence-warehouse`) exposing read-only warehouse queries and narrative writes for the asker agent.
- Six skills covering ingest, dashboard, refresh, tool interpretation, asker workflow, and PE diligence axes.
- Tooling-version provenance per refresh; absent binaries recorded as `"not-installed"`.
- Privacy gate on the working-pattern card — off by default, opt-in via settings flag.

### Security
- Hardened `.gitignore` against accidental commits of `.env`, keys, and credentials.
- Synthetic test fixtures use generic identities only; no real names or emails.
