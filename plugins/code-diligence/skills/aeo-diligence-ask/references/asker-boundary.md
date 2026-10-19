# Warehouse and asker boundary

The warehouse MCP opens the `--warehouse` path passed at server startup. The Claude Code plugin resolves that argument from `DILIGENCE_WAREHOUSE_PATH`; set the variable before starting its MCP server. After an initial ingest, start or reconnect the server with that warehouse path. Changing a child shell's environment does not change an already running MCP server.

Before answering, query `targets` through the native MCP to confirm the requested target is in the connected warehouse. Never substitute another target's data. If the server needs reconnecting, follow [prerequisite coverage](../../aeo-diligence-ingest/references/tool-prerequisites.md#explain-and-resolve-coverage-gaps): explain the missing query/narration capability and remedy, carry out authorized configuration or reconnection, and verify the recovered connection. A configuration entry or standalone protocol probe does not establish that the current agent can use its tools.

In Codex, or in Claude Code without the plugin, resolve the plugin root, then configure the existing server for the target. The launcher runs `uv` from the server's PATH and keeps the server in the plugin's own environment:

```sh
codex mcp add diligence-warehouse -- "$PLUGIN_ROOT/bin/run" \
  --directory "$PLUGIN_ROOT/mcp/diligence-warehouse" \
  python -m server --warehouse "$WAREHOUSE_PATH"

claude mcp add --scope local diligence-warehouse -- "$PLUGIN_ROOT/bin/run" \
  --directory "$PLUGIN_ROOT/mcp/diligence-warehouse" \
  python -m server --warehouse "$WAREHOUSE_PATH"
```

Claude Code connects a newly added server when its next session starts.

Use the runtime's MCP reconnect/reload capability and inspect its current-thread tools. The [Codex app-server protocol](https://developers.openai.com/codex/app-server/) supports `config/mcpServer/reload`, current-thread `mcpServerStatus/list`, and `mcpServer/tool/call`; use installed capabilities rather than assuming a session restart is necessary. Validate with native `list_tables` and a `targets` query after ingest has closed its writer. If that runtime action is unavailable, name the exact remaining connection step and its consequence. Do not substitute a script's database query for the agent's native MCP journey.

A local stdio MCP keeps database access local; it does not make the agent's model local. With a hosted agent, queried evidence enters that model's context. Explain this before offering hosted narration for a local-only request.

The asker has `list_tables`, `describe_table`, `read_query`, and local file-reading tools. It has no shell, file editor, or `write_narrative` access. Use the current runtime's actual tool names; Claude Code plugin MCP tools are namespaced under `plugin_code-diligence_diligence-warehouse`, and a directly configured server's tools under `diligence-warehouse`.

`read_query` accepts one read-only query, including CTEs and set operations, and interrupts execution after ten seconds. It cannot read external files or attach databases. For a write, return the proposed curation change to the parent workflow; do not bypass the read-only agent's tool boundary.
