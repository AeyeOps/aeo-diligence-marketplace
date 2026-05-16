---
name: asking-diligence
description: Spawn a read-only conversational analyst over a code-diligence target's warehouse and repo clones for open-ended drill-down into a finding (e.g., "why is this repo a hotspot?", "who carries bus-factor risk for X?"). Use when the user invokes /code-diligence:ask. Distinct from investigating which tool fed which warehouse column — use interpreting-tool-output for that.
argument-hint: <target> <question>
allowed-tools: Task, Bash, Read
---

The user has invoked `/code-diligence:ask <target> <question>`.

1. Resolve `<target>` to its settings file at `~/.claude/code-diligence-<target>.local.md`. If missing, tell the user to follow `skills/ingesting-target/SKILL.md` first and stop.
2. From the settings file, capture `target_id`, `target_name`, `storage.warehouse_path`, and `storage.repo_clone_root`. Export `DILIGENCE_WAREHOUSE_PATH=<warehouse_path>` for the agent's environment so the warehouse MCP picks it up.
3. Use the `Task` tool to spawn the `diligence-asker` agent (defined in `agents/diligence-asker.md`) with:
   - **Initial prompt:** the user's `<question>` verbatim
   - **Context block:** `target_id`, `target_name`, `repo_clone_root`
4. Stream the agent's response back to the user. For follow-ups in the same turn, re-use the same agent invocation via `SendMessage` (do not respawn). A fresh `/code-diligence:ask` call always spins up a new agent so the read-only boundary stays intact.
5. The asker is read-only by design — it can `query` the warehouse and read repo files, but cannot write narratives or modify the warehouse. If the user asks for a re-narration, redirect to `skills/refreshing-target/SKILL.md` (which calls the narrator with write access).

Agent boundary details and the warehouse MCP query surface: `references/asker-boundary.md`.
