#!/usr/bin/env bash
set -euo pipefail
exec uv run --directory "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py"
