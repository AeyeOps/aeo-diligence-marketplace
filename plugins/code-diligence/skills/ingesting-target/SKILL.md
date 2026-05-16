---
name: ingesting-target
description: Initial setup for a new code-diligence target — clone repos, walk git history, run the tool wrappers, populate the warehouse, and generate curation YAMLs. Use when the user invokes /code-diligence:ingest, or sets up code-diligence on a target for the first time (no warehouse exists yet). For already-ingested targets that need new commits picked up, use refreshing-target.
argument-hint: <target> [--quick | --full]
allowed-tools: Bash, Read
---

The user has invoked `/code-diligence:ingest <target> [--quick|--full]`.

1. Resolve `<target>` to a settings file at `~/.claude/code-diligence-<target>.local.md`. If it does not exist, tell the user to copy the template at `settings/diligence.example.local.md` (path relative to the plugin root) and edit it; do not proceed.
2. If neither `--quick` nor `--full` was passed, ask which tier and explain the trade-off in one sentence each:
   - **--quick** (<30 min for ~280 repos) — git walker + cheap tools (git-fame, git-of-theseus, git-truck); Process axis confidence will be low because expensive tools and the GitHub platform pass are skipped.
   - **--full** (1–3 hours) — adds hercules, code-maat, repowise, and the GitHub platform pass (PRs, Actions, releases, issues).
3. Run:

       uv run --directory ${CLAUDE_PLUGIN_ROOT} code-diligence ingest <settings-path> --<tier>

4. After the CLI exits successfully, surface from its stdout:
   - The path where the three curation YAMLs were written (`storage.curation_dir`)
   - The count of "needs review" entries in each YAML — partners triage those before viewing the dashboard
5. If the CLI exits non-zero, surface stderr verbatim. Do not paraphrase tool errors — wrappers already log `tool_failures` rows for non-fatal cases.

What gets populated and in what order: `references/pipeline-stages.md`.
Required external binaries and the skip behavior when they're missing: `references/tool-prerequisites.md`.
