#!/usr/bin/env bash
set -euo pipefail
exec "${CLAUDE_PLUGIN_ROOT}/bin/run" python "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py"
