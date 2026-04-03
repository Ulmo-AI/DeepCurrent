from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from ...runtime import get_telemetry, ok_result
from ...telemetry import finish_tool_timing, start_tool_timing
from .connectors import LocalJsonSearchConnector


_SOURCE = {"badge": "community", "publisher": "DeepCurrent", "execution_mode": "local"}

_CONNECTORS = {
    LocalJsonSearchConnector.spec.id: LocalJsonSearchConnector(),
}


def register_byod_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_byod_connectors",
        description="(Community) List built-in BYOD connectors (offline/local).",
        tags={"byod", "connectors", "community"},
    )
    async def list_byod_connectors() -> dict[str, Any]:
        specs = [
            {
                "id": c.spec.id,
                "description": c.spec.description,
                "input_schema": c.spec.input_schema,
                "execution_mode": c.spec.execution_mode,
                "badge": c.spec.badge,
                "publisher": c.spec.publisher,
                "docs_url": c.spec.docs_url,
            }
            for c in _CONNECTORS.values()
        ]
        return ok_result(
            text=f"{len(specs)} BYOD connector(s) available.",
            structured={"source": _SOURCE, "connectors": specs},
        )

    @mcp.tool(
        name="run_byod_connector",
        description="(Community) Run a BYOD connector locally (offline).",
        tags={"byod", "connectors", "community"},
    )
    async def run_byod_connector(
        connector_id: Annotated[str, "Connector ID (from list_byod_connectors)."],
        params: Annotated[dict, "Connector params matching its input_schema."] = {},
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="run_byod_connector", badge="community")
        telemetry = get_telemetry()

        connector = _CONNECTORS.get((connector_id or "").strip())
        if not connector:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "run_byod_connector",
                    "badge": "community",
                    "status": "error",
                    "reason": "unknown_connector",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(
                text=f"Unknown connector_id: {connector_id}",
                structured={
                    "source": _SOURCE,
                    "ok": False,
                    "error": {"code": "unknown_connector", "message": f"Unknown connector_id: {connector_id}"},
                },
            )

        result = await connector.run(params=params or {})
        ok = isinstance(result, dict) and bool(result.get("ok"))

        telemetry.capture_background(
            event="tool_executed",
            properties={
                "tool_name": "run_byod_connector",
                "badge": "community",
                "status": "success" if ok else "error",
                "connector_id": connector_id,
                "latency_ms": finish_tool_timing(timing),
            },
        )

        return ok_result(
            text=f"Connector '{connector_id}' completed.",
            structured={
                "source": _SOURCE,
                "connector_id": connector_id,
                "connector_badge": connector.spec.badge,
                "connector_execution_mode": connector.spec.execution_mode,
                "result": result,
            },
        )

