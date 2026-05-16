#!/usr/bin/env bash
# Emit a markdown summary of all targets currently configured in ~/.claude/code-diligence-*.local.md
set -euo pipefail
shopt -s nullglob
files=(~/.claude/code-diligence-*.local.md)
if [[ ${#files[@]} -eq 0 ]]; then
  exit 0
fi
echo "## code-diligence — active targets"
for f in "${files[@]}"; do
  name=$(basename "$f" | sed 's/^code-diligence-//;s/\.local\.md$//')
  warehouse=$(grep -oE 'warehouse_path: *[^[:space:]]+' "$f" | head -1 | awk '{print $2}' | sed "s|~|$HOME|")
  if [[ -f "$warehouse" ]]; then
    refreshed=$(stat -f %Sm -t %Y-%m-%d "$warehouse" 2>/dev/null || stat -c %y "$warehouse" 2>/dev/null | cut -d' ' -f1)
    echo "- **$name** — last refreshed $refreshed"
  else
    echo "- **$name** — not yet ingested"
  fi
done
