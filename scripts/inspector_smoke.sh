#!/usr/bin/env bash
# Minimal MCP Inspector (CLI) smoke: one `tools/call` that needs no API key to the cloud.
# For full checks (list + connect + credit status), use the commands in:
#   PRDs/Phase 15/QA Chat Phase 15 - Local and Remote MCP.md  §3.2
#
# Usage:
#   cd deepcurrent-local-mcp && bash scripts/inspector_smoke.sh
#
# Use an *absolute* path to the venv’s `deepcurrent-local-mcp` binary when calling the inspector
# yourself; relative paths often yield MCP error -32000 Connection closed.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/.venv/bin/deepcurrent-local-mcp"
PIPS="$ROOT/.venv/bin/pip"
INSPECTOR=(npx -y @modelcontextprotocol/inspector@latest --cli)

if [[ ! -x "$PIPS" ]]; then
  echo "Missing venv; run: cd $ROOT && python3 -m venv .venv && .venv/bin/pip install ." >&2
  exit 1
fi
"$PIPS" install -q . 2>/dev/null || true
if [[ ! -x "$BIN" ]]; then
  echo "Missing $BIN after pip install -e" >&2
  exit 1
fi

echo "== tools/call list_byod_connectors (validates stdio MCP + local BYOD) =="
"${INSPECTOR[@]}" "$BIN" --method tools/call --tool-name list_byod_connectors | head -c 800
echo
echo "… (truncated if long)"
echo
echo "inspector_smoke: ok"
