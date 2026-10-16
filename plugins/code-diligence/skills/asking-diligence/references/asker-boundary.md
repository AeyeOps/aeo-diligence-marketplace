# Warehouse and asker boundary

The warehouse MCP opens the path passed at server startup through `DILIGENCE_WAREHOUSE_PATH`. Set this environment variable before starting a Claude Code session with the plugin. After an initial ingest, start or reconnect the server with that warehouse path. Changing a child shell's environment does not change an already running MCP server.

Before answering, query `targets` to confirm the requested target is in the connected warehouse. Never substitute another target's data. If the server needs reconnecting, give the required warehouse path and report the connection gap.

The asker has `list_tables`, `describe_table`, `read_query`, and local file-reading tools. It has no shell, file editor, or `write_narrative` access. Use the current runtime's actual tool names; Claude Code plugin MCP tools are namespaced under `plugin_code-diligence_diligence-warehouse`.

`read_query` accepts one read-only query, including CTEs and set operations, and interrupts execution after ten seconds. It cannot read external files or attach databases. For a write, return the proposed curation change to the parent workflow; do not bypass the read-only agent's tool boundary.
