---
name: aeo-diligence-ask
description: Answer exploratory follow-up questions about an ingested code-diligence target using its warehouse and repository evidence. For tool-output mappings use aeo-diligence-tool-output.
allowed-tools: Read, Agent, mcp__plugin_code-diligence_diligence-warehouse__list_tables, mcp__plugin_code-diligence_diligence-warehouse__describe_table, mcp__plugin_code-diligence_diligence-warehouse__read_query, mcp__diligence-warehouse__list_tables, mcp__diligence-warehouse__describe_table, mcp__diligence-warehouse__read_query
---

# Ask about a diligence target

In Claude Code invoke `/code-diligence:aeo-diligence-ask` from the plugin or `/aeo-diligence-ask` as a standalone skill; in Codex invoke `$aeo-diligence-ask`.

Read the target's `diligence.local.md` in its target folder; [aeo-diligence-ingest](../aeo-diligence-ingest/SKILL.md) step 1 locates it. Confirm the connected warehouse contains that target with a read-only query before delegating. A shell `export` cannot retarget a server already running in the parent harness; use [the connection boundary](references/asker-boundary.md) when the MCP is unavailable or points to a different warehouse.

Invoke the plugin's `diligence-asker` agent through the current runtime's subagent tool, or without the plugin a subagent briefed with `agents/diligence-asker.md` under the plugin root and limited to its read-only tools. Pass the user's question verbatim, target ID, target name, warehouse path and repository root. Reuse that agent for follow-ups about the same target. If subagents are unavailable, answer with the same read-only tools and boundary.

Return the findings with warehouse or source citations and distinguish missing evidence from a negative result. Requests to change curations or regenerate narratives belong in [aeo-diligence-refresh](../aeo-diligence-refresh/SKILL.md).

Keep the connection reference aligned with changes observed during use.
