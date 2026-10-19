---
name: aeo-diligence-ingest
description: Set up a new code-diligence target or ingest its repositories for the first time. For a target that already has a warehouse, use aeo-diligence-refresh.
allowed-tools: Bash, Read, Agent
---

# Ingest a diligence target

Run the requested tier, preserve analyst curations, and finish with a dashboard the user can open. In Claude Code this skill is `/code-diligence:aeo-diligence-ingest` from the plugin or `/aeo-diligence-ingest` as a standalone skill; in Codex it is `$aeo-diligence-ingest`.

1. Each target has its own folder, holding its settings file `diligence.local.md` beside its warehouse. Use the folder the user names, or the folder of the warehouse the connected MCP reads. Read its `diligence.local.md`. If it is missing, create it from [the settings template](templates/diligence.example.local.md) using the target and sources the user supplied, with every storage path inside that folder. Ask only for required source or storage choices that are still unknown. Settings name the environment variable that holds a credential, never the credential itself.
2. If the user has not chosen a tier, ask whether they want quick (git history and available lightweight tools) or full (also the available deep analyzers and enabled GitHub data). Runtime depends on repository size and installed tools.
   Before ingest, use [host installation guidance](references/tool-prerequisites.md#choose-the-installation-environment) to select tools for the execution environment's OS and architecture. Follow [prerequisite coverage](references/tool-prerequisites.md#explain-and-resolve-coverage-gaps): verify the requested tier's tools and the native warehouse MCP, explain every confirmed gap and its consequence, recommend how to close it, and establish whether the user wants the gap closed or accepts reduced coverage. Existing installation or repair authorization carries forward; act on it without asking again.
3. Resolve the plugin root, the `plugins/code-diligence` folder that holds the runtime: `CLAUDE_PLUGIN_ROOT` in a plugin install, otherwise `CODE_DILIGENCE_ROOT`. If neither is set, tell the user to set `CODE_DILIGENCE_ROOT` to that folder of their aeo-diligence-marketplace checkout. Start every runtime command through `$PLUGIN_ROOT/bin/run`, which runs it in the plugin's own environment whatever environment the calling shell selects. Then run:

   ```sh
   "$PLUGIN_ROOT/bin/run" code-diligence ingest "$SETTINGS_PATH" --quick
   ```

   Substitute `--full` when requested. GitHub-enabled targets discover and clone the configured organizations. Local targets read existing checkouts under `storage.repo_clone_root`. On the full tier, a local checkout's GitHub platform data comes from its `origin` repository.
4. Inspect the CLI result, curation paths and review counts. A nonzero exit is a failed ingest; report the actual error. For newly discovered tool failures, follow the same coverage-gap procedure before declaring completion. Tool failures recorded in the warehouse remain visible on Health; a zero exit is not proof that every requested analyzer ran.
5. If this session's warehouse MCP is connected to the target, use the runtime's native subagent tool to run a narrator for each card in `axes_taxonomy`: the plugin's `diligence-narrator` agent, or without the plugin a subagent briefed with `agents/diligence-narrator.md` under the plugin root and limited to the warehouse tools. Pass target ID, warehouse path, axis, section key and tier. Supply `metric_context` from the matching [People](../aeo-diligence-axes/references/people.md), [Product](../aeo-diligence-axes/references/product.md), or [Process](../aeo-diligence-axes/references/process.md) reference and that card's SQL in the [dashboard templates](../aeo-diligence-dashboard/templates/observable/src/targets). The CLI has closed its database connection before agents write. Generate working-pattern prose only when `heuristics.allow_working_pattern_card` is true. For an unavailable or misdirected MCP, follow [the connection boundary](../aeo-diligence-ask/references/asker-boundary.md) and carry out authorized recovery before reporting a remaining blocker. Narration must respect the user's model/network choice; do not claim it ran when it did not.
6. Apply [aeo-diligence-dashboard](../aeo-diligence-dashboard/SKILL.md), including target, curation directory and privacy setting. Report the output path, preview URL, and any missing data sources.

Use [pipeline stages](references/pipeline-stages.md) for data ownership and [tool prerequisites](references/tool-prerequisites.md) for optional analyzers. Keep these references aligned when a real run reveals a changed command or tool format.
