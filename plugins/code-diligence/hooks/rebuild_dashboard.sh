#!/usr/bin/env bash
# Triggered by PostToolUse after warehouse-write events.
# Best-effort: if DILIGENCE_WAREHOUSE_PATH not set, exit 0 silently (nothing to rebuild).
set -euo pipefail
if [[ -z "${DILIGENCE_WAREHOUSE_PATH:-}" ]]; then
  exit 0
fi
warehouse="$DILIGENCE_WAREHOUSE_PATH"
# Output path defaults to ~/data/code-diligence/dashboard/ if not overridden
output="${DILIGENCE_DASHBOARD_OUTPUT:-$HOME/data/code-diligence/dashboard}"
# Run the render — non-fatal if it fails (we don't want to block the user's main loop)
uv run --directory "${CLAUDE_PLUGIN_ROOT}" python -m code_diligence.dashboard.render \
  --warehouse "$warehouse" --output "$output" || {
    echo "[code-diligence] dashboard rebuild failed (non-fatal); see logs" >&2
    exit 0
  }
