---
name: aeo-diligence-refresh
description: Refresh an existing code-diligence target after its source repositories change, preserving analyst-confirmed curations. Applies to requests to rerun or update target data, not to rebuild only the dashboard.
allowed-tools: Bash, Read, Agent
---

# Refresh a diligence target

In Claude Code invoke `/code-diligence:aeo-diligence-refresh` from the plugin or `/aeo-diligence-refresh` as a standalone skill; in Codex invoke `$aeo-diligence-refresh`.

Read the target's `diligence.local.md` in its target folder and confirm its warehouse exists. The `aeo-diligence-ingest` skill step 1 locates the folder and step 3 resolves `$PLUGIN_ROOT`. For an initial run, use that skill.

For a classification-only correction, use the current assessment and follow the `aeo-diligence-ingest` skill's `references/contributor-interview.md`; skip source collection. For a data refresh, prepare the target's curation and `fte_inference: false` setting as that reference describes before running the CLI.

Before refresh, follow the `aeo-diligence-ingest` skill's `references/tool-prerequisites.md` coverage procedure. Explain each confirmed missing capability, its effect on the results, and how to close it. Carry forward prior installation or repair authorization; otherwise establish whether the user wants it resolved or accepts reduced coverage. Apply the same procedure to failures first discovered during refresh.

Run the existing ingest path with `--full`:

```sh
"$PLUGIN_ROOT/bin/run" code-diligence ingest "$SETTINGS_PATH" --full
```

GitHub sources are fetched and fast-forwarded before analysis. Local checkouts with an origin are fetched and fast-forwarded too; a divergent checkout is reported, never reset. The CLI preserves entries with `source: analyst` and recomputes enabled heuristics; contributor decisions follow the interview below.

After a successful run, conduct the contributor interview for new or unresolved identities, preserving the user's earlier answers. Then prepare the requested Security periods again before narrating `product/security_findings`; use the same `dashboard.security_chart_path`, interval and range for narration and rendering. Follow the interview, narration and dashboard steps in the `aeo-diligence-ingest` skill. Report `targets.last_refreshed_at`, the built dashboard, recovered capabilities, and any remaining gaps with their consequences and the user's decision. A failed command is not a completed refresh; a zero exit does not establish full analyzer coverage.

The stage contract lives in the `aeo-diligence-ingest` skill's `references/pipeline-stages.md`. Correct that reference when a real run reveals a changed behavior.
