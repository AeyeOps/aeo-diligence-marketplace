---
name: building-dashboard
description: Build or rebuild the Observable dashboard from an existing code-diligence warehouse, including after curation or narrative changes. Does not refresh source repositories.
allowed-tools: Bash, Read
---

# Build a diligence dashboard

In Claude Code invoke `/code-diligence:building-dashboard`; in Codex invoke `$building-dashboard`.

Read the target's `~/.claude/code-diligence-<target>.local.md`. Resolve the plugin root from the runtime or this skill's location. Pass all three paths and the target ID:

```sh
uv run --directory "$PLUGIN_ROOT" python -m code_diligence.dashboard.render \
  --warehouse "$WAREHOUSE_PATH" --output "$OUTPUT_PATH" \
  --target-id "$TARGET_ID" --curation-dir "$CURATION_DIR"
```

Pass `--allow-working-pattern` only when `heuristics.allow_working_pattern_card` is true. The renderer replaces its configured output directory, so use `dashboard.output_path` rather than a source or repository directory.

On success, give the output path and `python -m http.server --directory "$OUTPUT_PATH"` preview command. Inspect the generated target pages in the available browser when UI validation is requested. On failure, report the command's error; do not claim that the prior dashboard is current.

- [Renderer arguments](references/render-args.md): inputs, output replacement and build behavior.
- [Privacy setting](references/privacy-gate.md): the existing opt-in contract.
- [Template layout](references/template-layout.md): page and asset ownership.

Update the owning reference when an observed runtime change makes it inaccurate.
