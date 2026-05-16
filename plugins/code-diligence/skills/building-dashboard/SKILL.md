---
name: building-dashboard
description: Build the Observable Framework dashboard for a code-diligence target's warehouse, honoring the privacy gate on the working-pattern card. Use when the user invokes /code-diligence:dashboard, or auto-fired by the PostToolUse hook after a warehouse write.
argument-hint: <target>
allowed-tools: Bash, Read
---

The user (or the PostToolUse hook) has invoked `/code-diligence:dashboard <target>`.

1. Resolve `<target>` to its settings file at `~/.claude/code-diligence-<target>.local.md`. If missing, tell the user and stop.
2. Read these fields from the settings:
   - `storage.warehouse_path` — input DuckDB warehouse
   - `dashboard.output_path` — directory to receive the rendered `dist/`
   - `heuristics.allow_working_pattern_card` — privacy gate (default `false`); see `references/privacy-gate.md`
3. Build the dashboard. Pass `--allow-working-pattern` only when the flag is true:

       uv run --directory ${CLAUDE_PLUGIN_ROOT} \
         python -m code_diligence.dashboard.render \
         --warehouse <warehouse_path> \
         --output <output_path> \
         [--allow-working-pattern]

4. On success, tell the user the output directory and the preview command:

       python -m http.server -d <output_path>

5. On non-zero exit, surface the stderr verbatim. The renderer fails the build when the template's npm install or `observable build` fails — do not silently retry.

Full renderer argument surface (curation, custom output, env vars): `references/render-args.md`.
Template layout and what gets copied where: `references/template-layout.md`.
