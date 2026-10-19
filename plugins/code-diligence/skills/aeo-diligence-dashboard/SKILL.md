---
name: aeo-diligence-dashboard
description: Build or rebuild the Observable dashboard from an existing code-diligence warehouse, including after curation or narrative changes. Does not refresh source repositories.
allowed-tools: Bash, Read
---

# Build a diligence dashboard

In Claude Code invoke `/code-diligence:aeo-diligence-dashboard` from the plugin or `/aeo-diligence-dashboard` as a standalone skill; in Codex invoke `$aeo-diligence-dashboard`.

Read the target's `diligence.local.md` in its target folder. [aeo-diligence-ingest](../aeo-diligence-ingest/SKILL.md) step 1 locates the folder and step 3 resolves `$PLUGIN_ROOT`. Pass all three paths and the target ID:

```sh
uv run --directory "$PLUGIN_ROOT" python -m code_diligence.dashboard.render \
  --warehouse "$WAREHOUSE_PATH" --output "$OUTPUT_PATH" \
  --target-id "$TARGET_ID" --curation-dir "$CURATION_DIR"
```

Pass `--allow-working-pattern` only when `heuristics.allow_working_pattern_card` is true. The renderer replaces its configured output directory, so use `dashboard.output_path` rather than a source or repository directory.

On success, give the output path and `python -m http.server --directory "$OUTPUT_PATH"` preview command. The build never needs a browser. When end-to-end validation is requested, prefer a browser automation tool that is already installed, such as `agent-browser`; if none is, work with the operator to install one before validating. If Health or a card exposes a confirmed collection or narration gap, follow [prerequisite coverage](../aeo-diligence-ingest/references/tool-prerequisites.md#explain-and-resolve-coverage-gaps): explain the missing result and the remedy, then carry out authorized recovery or establish whether the user accepts reduced coverage. Building alone does not recover missing evidence. On failure, report the command's error; do not claim that the prior dashboard is current.

- [Renderer arguments](references/render-args.md): inputs, output replacement and build behavior.
- [Privacy setting](references/privacy-gate.md): the existing opt-in contract.
- [Template layout](references/template-layout.md): page and asset ownership.

Update the owning reference when an observed runtime change makes it inaccurate.
