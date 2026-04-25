from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

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
        description=(
            "(Official) Free redacted preview (aggregates only). "
            "Use first for ambiguous investor, builder, named-company people, intro, or contact asks before quoting. "
            "For named-company people discovery, this stays primary even if the request sounds operational, and "
            "the backend response now carries coverage/fallback metadata for clients to follow. For broad "
            "contact or intro asks, first clarify the target type and whether the user wants discovery, a warm "
            "route, or direct contact unlock on an existing result."
        ),
        annotations=ToolAnnotations(
            title="Resolve Intelligence Intent",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        tags={"intelligence", "official", "resolve"},
    )
    async def resolve_intelligence_intent(
        package_id: Annotated[
            str,
            "Supported package ID, including company-people-discovery-v1 for named-company people discovery.",
        ],
        slots: Annotated[dict, "Slot values. Missing required slots return clarification questions."] = {},
        request_text: Annotated[
            str | None,
            "Optional raw user request text to help backend intent resolution when slots are incomplete.",
        ] = None,
        workflow_id: Annotated[
            str | None,
            "Optional workflow contract ID when the caller already knows the intended workflow.",
        ] = None,
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="resolve_intelligence_intent", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.post_json(
                "/api/v1/intelligence/resolve",
                json_body={
                    "package_id": package_id,
                    "slots": slots or {},
                    "request_text": request_text,
                    "workflow_id": workflow_id,
                },
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
        name="preview_quote_intelligence_package",
        description=(
            "(Official) Preferred: runs redacted preview plus quote in one step when the request is ready. "
            "If the corpus has no matches, quote is omitted; use the growth tools for manual lead enrichment. "
            "Quote responses can also include zero-credit context such as exact-result reuse or already-unlocked contacts. "
            "For ambiguous investor or contact asks, clarify the target type and desired outcome before using this."
        ),
        annotations=ToolAnnotations(
            title="Preview And Quote Intelligence Package",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
        tags={"intelligence", "official", "quote", "preview"},
    )
    async def preview_quote_intelligence_package(
        package_id: Annotated[
            str,
            "Package ID to preview and quote. Use company-people-discovery-v1 first for named-company people or leadership discovery.",
        ],
        slots: Annotated[dict, "Slot values (must satisfy required slots for quote)."],
        output_fields: Annotated[list[str], "Requested Tier 1 output fields (for execute)."] = [],
        parent_result_id: Annotated[str | None, "When quoting an expansion, provide parent_result_id."] = None,
        expansion_scope: Annotated[dict | None, "Optional expansion scope."] = None,
        request_text: Annotated[
            str | None,
            "Optional raw user request text to help backend slot normalization before preview/quote.",
        ] = None,
        workflow_id: Annotated[
            str | None,
            "Optional workflow contract ID when the caller already knows the intended workflow.",
        ] = None,
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="preview_quote_intelligence_package", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            req: dict[str, Any] = {
                "package_id": package_id,
                "slots": slots or {},
                "output_fields": output_fields or [],
                "request_text": request_text,
                "workflow_id": workflow_id,
            }
            if parent_result_id:
                req["parent_result_id"] = parent_result_id
            if expansion_scope is not None:
                req["expansion_scope"] = expansion_scope

            raw = await client.post_json("/api/v1/intelligence/preview-quote", json_body=req)
            body = dict(raw) if isinstance(raw, dict) else {"payload": raw}
            q = body.get("quote")
            if isinstance(q, dict):
                body["quote_token"] = q.get("quote_token")
                body["credits"] = q.get("credits")
                body["output_projection_summary"] = q.get("output_projection_summary")
                body["expiry"] = q.get("expiry")
            credits = body.get("credits") if isinstance(body, dict) else None
            skipped = body.get("quote_skipped_reason") if isinstance(body, dict) else None

            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "preview_quote_intelligence_package",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            if skipped == "no_corpus_candidates":
                return ok_result(
                    text="Preview shows no corpus matches; quote not minted. For manual lead search, use resolve_growth_outcome then quote_growth_plan.",
                    structured=_payload_with_source(body),
                )
            return ok_result(
                text=f"Preview + quoted {credits} credits." if credits is not None else "Preview complete (clarification or no quote).",
                structured=_payload_with_source(body),
            )
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "preview_quote_intelligence_package",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="quote_intelligence_package",
        description=(
            "(Official) Quote pricing (returns quote_token). Use after the intent is clear and before execute/expand."
        ),
        annotations=ToolAnnotations(
            title="Quote Intelligence Package",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
        tags={"intelligence", "official", "quote"},
    )
    async def quote_intelligence_package(
        package_id: Annotated[
            str,
            "Package ID to quote. Use company-people-discovery-v1 first for named-company people or leadership discovery.",
        ],
        slots: Annotated[dict, "Slot values (must satisfy required slots)."],
        output_fields: Annotated[list[str], "Tier 1 output fields (execute quotes)."] = [],
        parent_result_id: Annotated[str | None, "When quoting an expansion, provide parent_result_id."] = None,
        expansion_scope: Annotated[dict | None, "Optional expansion scope."] = None,
        request_text: Annotated[
            str | None,
            "Optional raw user request text to help backend slot normalization before quoting.",
        ] = None,
        workflow_id: Annotated[
            str | None,
            "Optional workflow contract ID when the caller already knows the intended workflow.",
        ] = None,
        anchor_quote_token: Annotated[
            str | None,
            "Optional. quote_token from the last preview_quote when the follow-up is only confirmation (e.g. yes) or model slots are unreliable; backend pins execute slots from the prior preview.",
        ] = None,
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="quote_intelligence_package", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            req: dict[str, Any] = {
                "package_id": package_id,
                "slots": slots or {},
                "output_fields": output_fields or [],
                "request_text": request_text,
                "workflow_id": workflow_id,
            }
            if parent_result_id:
                req["parent_result_id"] = parent_result_id
            if expansion_scope is not None:
                req["expansion_scope"] = expansion_scope
            if anchor_quote_token and str(anchor_quote_token).strip():
                req["anchor_quote_token"] = str(anchor_quote_token).strip()

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
        description=(
            "(Official) Execute Tier 1 (Curated Discovery). Only use after explicit user confirmation of the quote."
        ),
        annotations=ToolAnnotations(
            title="Execute Intelligence Package",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
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
        description=(
            "(Official) Fetch a saved intelligence result by result_id from "
            "/api/v1/intelligence/results/{result_id}. Use this for result_ids returned by "
            "execute_intelligence_package or expand_intelligence_package. Do not use "
            "fetch_result_summary for these intelligence result_ids. "
            "Use when the user wants the saved result inspected in chat; records are truncated to avoid huge context."
        ),
        annotations=ToolAnnotations(
            title="Fetch Intelligence Result",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        description=(
            "(Official) Expand Tier 2 or increase limit. "
            "Usually use only after the user has reviewed a base result and explicitly approved the expansion quote."
        ),
        annotations=ToolAnnotations(
            title="Expand Intelligence Package",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
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

