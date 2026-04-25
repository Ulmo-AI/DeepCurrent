#!/usr/bin/env bash
# Local automation for MCP QA: no API keys, no network to DeepCurrent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m compileall -q src
pytest -q "$@"
