---
name: refreshing-target
description: Refresh an existing code-diligence target after its source repositories change, preserving analyst-confirmed curations. Applies to requests to rerun or update target data, not to rebuild only the dashboard.
allowed-tools: Bash, Read, Agent
---

# Refresh a diligence target

In Claude Code invoke `/code-diligence:refreshing-target` from the plugin or `/refreshing-target` as a standalone skill; in Codex invoke `$refreshing-target`.

Read the target's `diligence.local.md` in its target folder and confirm its warehouse exists. [Ingesting-target](../ingesting-target/SKILL.md) step 1 locates the folder and step 3 resolves `$PLUGIN_ROOT`. For an initial run, use that skill.

Before refresh, follow [prerequisite coverage](../ingesting-target/references/tool-prerequisites.md#explain-and-resolve-coverage-gaps). Explain each confirmed missing capability, its effect on the results, and how to close it. Carry forward prior installation or repair authorization; otherwise establish whether the user wants it resolved or accepts reduced coverage. Apply the same procedure to failures first discovered during refresh.

Run the existing ingest path with `--full`:

```sh
uv run --directory "$PLUGIN_ROOT" code-diligence ingest "$SETTINGS_PATH" --full
```

GitHub sources are fetched and fast-forwarded before analysis. Local checkouts with an origin are fetched and fast-forwarded too; a divergent checkout is reported, never reset. Analyst entries with `source: analyst` remain authoritative; heuristic entries are recomputed.

After a successful run, follow the narration and dashboard steps in [ingesting-target](../ingesting-target/SKILL.md). Report `targets.last_refreshed_at`, the built dashboard, recovered capabilities, and any remaining gaps with their consequences and the user's decision. A failed command is not a completed refresh; a zero exit does not establish full analyzer coverage.

The stage contract lives in [pipeline stages](../ingesting-target/references/pipeline-stages.md). Correct that reference when a real run reveals a changed behavior.
