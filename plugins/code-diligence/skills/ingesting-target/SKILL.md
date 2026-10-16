---
name: ingesting-target
description: Set up a new code-diligence target or ingest its repositories for the first time. For a target that already has a warehouse, use refreshing-target.
allowed-tools: Bash, Read, Agent
---

# Ingest a diligence target

Run the requested tier, preserve analyst curations, and finish with a dashboard the user can open. In Claude Code this skill is `/code-diligence:ingesting-target`; in Codex it is `$ingesting-target`.

1. Read `~/.claude/code-diligence-<target>.local.md`. If it is missing, create it from [the settings template](../../settings/diligence.example.local.md) using the target and sources the user supplied. Ask only for required source or storage choices that are still unknown. Keep credentials in the named environment variable.
2. If the user has not chosen a tier, ask whether they want quick (git history and available lightweight tools) or full (also the available deep analyzers and enabled GitHub data). Runtime depends on repository size and installed tools.
3. Resolve the plugin root from `CLAUDE_PLUGIN_ROOT` in Claude Code or this skill's directory in another runtime, then run:

   ```sh
   uv run --directory "$PLUGIN_ROOT" code-diligence ingest "$SETTINGS_PATH" --quick
   ```

   Substitute `--full` when requested. GitHub-enabled targets discover and clone the configured organizations. Local targets read existing checkouts under `storage.repo_clone_root`.
4. Inspect the CLI result, curation paths and review counts. A nonzero exit is a failed ingest; report the actual error. Tool failures recorded in the warehouse remain visible on Health.
5. If this session's warehouse MCP is connected to the target, use the runtime's native subagent tool to invoke `diligence-narrator` for each card in `axes_taxonomy`, passing target ID, warehouse path, axis, section key and tier. Supply `metric_context` from the matching [People](../understanding-pe-diligence-axes/references/people.md), [Product](../understanding-pe-diligence-axes/references/product.md), or [Process](../understanding-pe-diligence-axes/references/process.md) reference and that card's SQL in the [dashboard templates](../building-dashboard/templates/observable/src/targets). The CLI has closed its database connection before agents write. Generate working-pattern prose only when `heuristics.allow_working_pattern_card` is true. If the MCP is unavailable or points elsewhere, report that narration is unavailable; do not claim it ran. See [the warehouse connection boundary](../asking-diligence/references/asker-boundary.md).
6. Apply [building-dashboard](../building-dashboard/SKILL.md), including target, curation directory and privacy setting. Report the output path, preview URL, and any missing data sources.

Use [pipeline stages](references/pipeline-stages.md) for data ownership and [tool prerequisites](references/tool-prerequisites.md) for optional analyzers. Keep these references aligned when a real run reveals a changed command or tool format.
