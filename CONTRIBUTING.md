# Contributing 🤝

Thanks for helping build the DeepCurrent Local MCP ecosystem.

## Principles

- Do not ship proprietary DeepCurrent datasets, joins, or intelligence logic.
- Prefer BYOD: users bring their own API keys + data sources.
- Never log tool inputs/outputs or API keys.
- Keep outputs bounded (truncate large lists; provide fetch-by-id patterns when needed).

## Badges (Community → Certified → Official)

Badges are a promotion pipeline and a trust boundary:

- **community**: local-only, unreviewed BYOD/BYOK connectors
- **certified**: local-only, reviewed connectors (stable schemas + bounded outputs). Still BYOD/BYOK.
- **official**: cloud-backed tools operated by DeepCurrent and eligible for paid credits

Guideline:
- If it requires running third-party code, it stays **local** (community/certified).
- If it needs a “no install” hosted experience + credit integration, it becomes **official** (cloud-backed).

## Where to Add Things

- **Official plugins:** `src/deepcurrent_local_mcp/plugins/official/`
- **Community plugins:** `src/deepcurrent_local_mcp/plugins/community/`
  - Start from `TEMPLATE.md`

## How to Contribute a Connector (Recommended Flow)

1. Create a connector in `src/deepcurrent_local_mcp/plugins/community/connectors/`
2. Define a clear `ConnectorSpec` (id, description, input schema, badge, execution_mode, publisher)
3. Register it in `src/deepcurrent_local_mcp/plugins/community/byod.py`
4. Keep outputs bounded:
   - hard cap result counts
   - include truncation flags
   - prefer “fetch by id/path” patterns for large datasets

### Getting “Certified”

To request `certified` status, include in your PR:

- deterministic output schema (no random IDs unless required)
- bounded output behavior + truncation flags
- docs: how to obtain required API keys / permissions (if BYOK)
- clear failure states (missing key, rate limit, bad params)

## Testing

Basic syntax check:

```bash
python3 -m py_compile src/deepcurrent_local_mcp/**/*.py
```

You can also run:

```bash
python3 -m compileall -q src
pytest -q
# or, from repo root:
bash scripts/qa_mcp.sh
```

For product QA, run Inspector or your target MCP client against the absolute path to `.venv/bin/deepcurrent-local-mcp`, then call `tools/list` and any relevant smoke-test tools.

MCP **Inspector** quick smoke (stdio + one tool call, no API key): `bash scripts/inspector_smoke.sh` (requires `npx` and a venv with `pip install .`).
