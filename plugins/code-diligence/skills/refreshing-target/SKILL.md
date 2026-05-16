---
name: refreshing-target
description: Re-run the code-diligence ingest pipeline against an already-ingested target so its warehouse picks up new commits and tool output without a full reset. Use when the user invokes /code-diligence:refresh.
argument-hint: <target>
allowed-tools: Bash, Read
---

The user has invoked `/code-diligence:refresh <target>`.

1. Resolve `<target>` to its settings file at `~/.claude/code-diligence-<target>.local.md`. If missing, tell the user to follow `skills/ingesting-target/SKILL.md` first and stop.
2. Confirm the warehouse already exists at the `storage.warehouse_path` from settings. If absent, the operation is an initial ingest, not a refresh — direct the user to `skills/ingesting-target/SKILL.md`.
3. Run a full-tier rerun (incremental cloner + every tool pass; the underlying CLI is idempotent — repeated commits do not double-count):

       uv run --directory ${CLAUDE_PLUGIN_ROOT} code-diligence ingest <settings-path> --full

4. On success, report `targets.last_refreshed_at` (a timestamp in the warehouse) so the user can confirm the refresh actually landed.
5. On non-zero exit, surface the CLI's stderr verbatim. Do not paraphrase tool failures — they are logged into `tool_failures` for later inspection.

The dedicated `refresh` subcommand is a Phase 5 candidate; until it lands, `ingest --full` is the supported path because both share the same idempotent walker + tool wrappers.
