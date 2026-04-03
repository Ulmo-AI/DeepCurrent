from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from ...cloud import CloudAPIError
from ...runtime import error_result, get_telemetry, ok_result, require_cloud_client
from ...telemetry import finish_tool_timing, start_tool_timing

_SOURCE = {"badge": "official", "publisher": "DeepCurrent", "execution_mode": "deepcurrent-cloud"}


def _truncate_records(payload: dict[str, Any], *, max_records: int = 25) -> dict[str, Any]:
    """
    Keep tool outputs bounded to avoid dumping huge payloads into model context.
    """
    try:
        records = payload.get("records")
        if not isinstance(records, list):
            return payload
        if len(records) <= max_records:
            return payload
        return {
            **payload,
            "records": records[:max_records],
            "records_truncated": True,
            "records_truncated_to": max_records,
        }
    except Exception:
        return payload


def _payload_with_source(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {"source": _SOURCE, **payload}
    return {"source": _SOURCE, "payload": payload}


def register_intelligence_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="resolve_intelligence_intent",
        description="(Official) Phase 8 intelligence: free redacted preview (aggregates only). Use first.",
        tags={"intelligence", "official", "resolve"},
    )
    async def resolve_intelligence_intent(
        package_id: Annotated[str, "One of the Phase 8 package IDs."],
        slots: Annotated[dict, "Slot values. Missing required slots return clarification questions."] = {},
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="resolve_intelligence_intent", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.post_json(
                "/api/v1/intelligence/resolve",
                json_body={"package_id": package_id, "slots": slots or {}},
            )
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "resolve_intelligence_intent",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text="Resolved intelligence intent.", structured=_payload_with_source(payload))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "resolve_intelligence_intent",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="quote_intelligence_package",
        description="(Official) Phase 8 intelligence: quote-first pricing (returns quote_token). Use before execute/expand.",
        tags={"intelligence", "official", "quote"},
    )
    async def quote_intelligence_package(
        package_id: Annotated[str, "Package ID to quote."],
        slots: Annotated[dict, "Slot values (must satisfy required slots)."],
        output_fields: Annotated[list[str], "Tier 1 output fields (execute quotes)."] = [],
        parent_result_id: Annotated[str | None, "When quoting an expansion, provide parent_result_id."] = None,
        expansion_scope: Annotated[dict | None, "Optional expansion scope."] = None,
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="quote_intelligence_package", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            req: dict[str, Any] = {
                "package_id": package_id,
                "slots": slots or {},
                "output_fields": output_fields or [],
            }
            if parent_result_id:
                req["parent_result_id"] = parent_result_id
            if expansion_scope is not None:
                req["expansion_scope"] = expansion_scope

            payload = await client.post_json("/api/v1/intelligence/quote", json_body=req)
            credits = payload.get("credits") if isinstance(payload, dict) else None
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "quote_intelligence_package",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(
                text=f"Quoted {credits} credits." if credits is not None else "Quoted package.",
                structured=_payload_with_source(payload),
            )
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "quote_intelligence_package",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="execute_intelligence_package",
        description="(Official) Phase 8 intelligence: execute Tier 1 (Curated Discovery). Requires paid entitlement.",
        tags={"intelligence", "official", "execute"},
    )
    async def execute_intelligence_package(
        package_id: Annotated[str, "Package ID to execute (must match the quote payload)."],
        slots: Annotated[dict, "Slot values (must match the quote payload)."],
        output_fields: Annotated[list[str], "Tier 1 output fields (must match the quote payload)."],
        quote_token: Annotated[str, "Quote token returned by quote_intelligence_package."],
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="execute_intelligence_package", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.post_json(
                "/api/v1/intelligence/execute",
                json_body={
                    "package_id": package_id,
                    "slots": slots or {},
                    "output_fields": output_fields or [],
                    "quote_token": quote_token,
                },
            )
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "execute_intelligence_package",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text="Executed intelligence package.", structured=_payload_with_source(payload))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "execute_intelligence_package",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="fetch_intelligence_result",
        description="(Official) Phase 8 intelligence: fetch saved result by result_id (records truncated to avoid huge context).",
        tags={"intelligence", "official", "results"},
    )
    async def fetch_intelligence_result(
        result_id: Annotated[str, "Result UUID returned by execute/expand."],
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="fetch_intelligence_result", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.get_json(f"/api/v1/intelligence/results/{result_id}")
            if isinstance(payload, dict):
                payload = _truncate_records(payload, max_records=25)
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "fetch_intelligence_result",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text="Fetched intelligence result.", structured=_payload_with_source(payload))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "fetch_intelligence_result",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="expand_intelligence_package",
        description="(Official) Phase 8 intelligence: expand (Tier 2) or increase limit. Requires paid entitlement.",
        tags={"intelligence", "official", "expand"},
    )
    async def expand_intelligence_package(
        parent_result_id: Annotated[str, "Parent result UUID to expand."],
        expansion_type: Annotated[str, "contact_unlock | network_depth | increase_limit"],
        expansion_params: Annotated[dict, "Expansion parameters for the chosen expansion_type."] = {},
        quote_token: Annotated[str, "Quote token returned by quote_intelligence_package for this expansion."] = "",
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="expand_intelligence_package", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.post_json(
                "/api/v1/intelligence/expand",
                json_body={
                    "parent_result_id": parent_result_id,
                    "expansion_type": expansion_type,
                    "expansion_params": expansion_params or {},
                    "quote_token": quote_token,
                },
            )
            if isinstance(payload, dict) and "records" in payload:
                payload = _truncate_records(payload, max_records=25)
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "expand_intelligence_package",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text="Expanded intelligence result.", structured=_payload_with_source(payload))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "expand_intelligence_package",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

