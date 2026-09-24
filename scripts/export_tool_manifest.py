from __future__ import annotations

import asyncio
import json
from typing import Any

from deepcurrent_local_mcp.main import mcp

LOCAL_ONLY_TOOLS = {"list_byod_connectors", "run_byod_connector"}


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    return value


async def build_manifest() -> dict[str, Any]:
    tools = []
    for tool in sorted(await mcp.list_tools(), key=lambda item: item.name):
        if tool.name in LOCAL_ONLY_TOOLS:
            continue
        tools.append(
            {
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                "input_schema": tool.parameters,
                "output_schema": tool.output_schema,
                "annotations": _json_value(tool.annotations),
            }
        )
    return {"manifest_version": 1, "server_version": str(mcp.version), "tools": tools}


def main() -> None:
    print(json.dumps(asyncio.run(build_manifest()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
