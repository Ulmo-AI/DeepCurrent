# Community Connector Template

This template describes how to add a community/BYOD connector to DeepCurrent Local MCP.

## Principles

- Do not ship proprietary DeepCurrent datasets, joins, or intelligence logic.
- Prefer BYOD: users bring their own API keys + data sources.
- Keep outputs bounded (truncate large lists; include IDs/paths to retrieve more).
- Never log tool inputs/outputs or secrets.

## Where to put code

- Community connectors live in `src/deepcurrent_local_mcp/plugins/community/connectors/`.
- Register connectors in `src/deepcurrent_local_mcp/plugins/community/byod.py`.

## ConnectorSpec checklist

Each connector exposes a `spec` with:

- `id`: stable identifier (snake_case)
- `description`: short, user-facing summary
- `input_schema`: JSON Schema dict (what params the connector accepts)
- `execution_mode`: `local` | `byok-api` | `deepcurrent-gateway`
- `badge`: `community` | `certified` | `official`
- `publisher`: display name (who shipped it)
- `docs_url`: optional link

## Minimal example

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import ConnectorSpec


@dataclass(frozen=True)
class ExampleConnector:
    spec: ConnectorSpec = ConnectorSpec(
        id="example",
        description="Example connector (replace with real one).",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        execution_mode="local",
        badge="community",
        publisher="YourNameOrOrg",
        docs_url=None,
    )

    async def run(self, *, params: dict[str, Any]) -> dict[str, Any]:
        query = str((params or {}).get("query") or "").strip()
        if not query:
            return {"ok": False, "error": {"code": "missing_query", "message": "Missing query"}}
        return {"ok": True, "result": {"echo": query}}
```

## Notes

- Keep return payloads deterministic (avoid random IDs or timestamps unless needed).
- Avoid returning huge arrays; prefer a max limit + truncation flags.

