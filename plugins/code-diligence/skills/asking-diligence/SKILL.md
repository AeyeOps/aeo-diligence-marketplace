---
name: asking-diligence
description: Answer exploratory follow-up questions about an ingested code-diligence target using its warehouse and repository evidence. For tool-output mappings use interpreting-tool-output.
allowed-tools: Read, Agent, mcp__plugin_code-diligence_diligence-warehouse__list_tables, mcp__plugin_code-diligence_diligence-warehouse__describe_table, mcp__plugin_code-diligence_diligence-warehouse__read_query
---

# Ask about a diligence target

In Claude Code invoke `/code-diligence:asking-diligence`; in Codex invoke `$asking-diligence`.

Read the target settings at `~/.claude/code-diligence-<target>.local.md`. Confirm the connected warehouse contains that target with a read-only query before delegating. A shell `export` cannot retarget a server already running in the parent harness; use [the connection boundary](references/asker-boundary.md) when the MCP is unavailable or points to a different warehouse.

Invoke the `diligence-asker` agent through the current runtime's subagent tool. Pass the user's question verbatim, target ID, target name, warehouse path and repository root. Reuse that agent for follow-ups about the same target. If subagents are unavailable, answer with the same read-only tools and boundary.

Return the findings with warehouse or source citations and distinguish missing evidence from a negative result. Requests to change curations or regenerate narratives belong in [refreshing-target](../refreshing-target/SKILL.md).

Keep the connection reference aligned with changes observed during use.
