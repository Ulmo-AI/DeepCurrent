from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from ...cloud import CloudAPIError
from ...runtime import error_result, get_telemetry, ok_result, require_cloud_client
from ...telemetry import finish_tool_timing, start_tool_timing

_SOURCE = {"badge": "official", "publisher": "DeepCurrent", "execution_mode": "deepcurrent-cloud"}


def _payload_with_source(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {"source": _SOURCE, **payload}
    return {"source": _SOURCE, "payload": payload}


def register_growth_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="resolve_growth_outcome",
        description=(
            "Growth orchestration: resolve a founder/company/contact enrichment goal into "
            "a compact provider-backed plan. Use this first. Small plain-text company lists are fine. "
            "For bulk structured data, prefer CSV-style inputs and inspect only the header row plus "
            "1-3 sample rows to map fields before execution."
        ),
        tags={"growth", "resolve", "preview"},
    )
    async def resolve_growth_outcome(
        goal_text: Annotated[str, "Describe the desired outcome, such as finding founders, enriching leads, or verifying emails."],
        constraints: Annotated[
            dict | None,
            "Optional goal constraints like niche, geo, count, required_fields, urgency, or budget_mode.",
        ] = None,
        input_assets: Annotated[
            dict | None,
            (
                "Optional input assets. Example: {\"companies\": [...], \"contacts\": [...]} for provider-backed "
                "enrichment. Map common aliases like name->company_name or website_url->website. If a CSV/header "
                "mapping is ambiguous, ask the user to confirm before quoting or running."
            ),
        ] = None,
        input_text: Annotated[
            str | None,
            "Optional plain-text list input. Use for pasted company or email lists that are not yet structured.",
        ] = None,
        input_table: Annotated[
            list[dict[str, Any]] | None,
            "Optional structured table rows, such as CSV-derived objects before canonical field mapping.",
        ] = None,
        column_mapping: Annotated[
            dict[str, str] | None,
            "Optional source-column to canonical-field mapping for input_table rows.",
        ] = None,
        asset_handle: Annotated[
            str | dict[str, Any] | None,
            "Optional uploaded asset reference or inline asset payload for future file-based growth flows.",
        ] = None,
        icp_config: Annotated[
            dict | None,
            "Optional ICP config to pass through to the provider boundary.",
        ] = None,
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="resolve_growth_outcome", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.post_json(
                "/api/v1/growth/resolve",
                json_body={
                    "goal_text": goal_text,
                    "constraints": constraints or {},
                    "input_assets": input_assets or {},
                    "input_text": input_text,
                    "input_table": input_table or [],
                    "column_mapping": column_mapping or {},
                    "asset_handle": asset_handle,
                    "icp_config": icp_config,
                },
            )
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "resolve_growth_outcome",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text="Resolved growth outcome.", structured=_payload_with_source(payload))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "resolve_growth_outcome",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="quote_growth_plan",
        description=(
            "Growth orchestration: quote a resolved plan before any provider-backed execution. "
            "You MUST get explicit user confirmation before run_growth_plan."
        ),
        tags={"growth", "quote", "pricing"},
    )
    async def quote_growth_plan(
        goal_plan: Annotated[dict[str, Any], "The goal_plan returned by resolve_growth_outcome."],
        max_external_spend_credits: Annotated[
            int | None,
            "Optional cap for provider-backed spend in credits.",
        ] = None,
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="quote_growth_plan", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            body = await client.post_json(
                "/api/v1/growth/quote",
                json_body={
                    "goal_plan": goal_plan,
                    "max_external_spend_credits": max_external_spend_credits,
                },
            )
            b = dict(body) if isinstance(body, dict) else {"payload": body}
            credits = b.get("credits_total")
            text = (
                f"Quoted {credits} credits for the growth plan."
                if credits is not None
                else "Quoted growth plan."
            )
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "quote_growth_plan",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text=text, structured=_payload_with_source(b))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "quote_growth_plan",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="run_growth_plan",
        description=(
            "Growth orchestration: run an approved provider-backed growth plan. "
            "ONLY call this after the user explicitly approves the quote."
        ),
        tags={"growth", "execute"},
    )
    async def run_growth_plan(
        quote_token: Annotated[str, "Quote token returned by quote_growth_plan."],
        goal_plan: Annotated[dict[str, Any], "The normalized goal_plan returned by quote_growth_plan."],
        execution_mode: Annotated[
            str,
            "Execution mode for the run. Keep the default 'internal_first'.",
        ] = "internal_first",
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="run_growth_plan", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.post_json(
                "/api/v1/growth/run",
                json_body={
                    "quote_token": quote_token,
                    "goal_plan": goal_plan,
                    "execution_mode": execution_mode,
                },
            )
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "run_growth_plan",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text="Started growth plan execution.", structured=_payload_with_source(payload))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "run_growth_plan",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="get_growth_plan_status",
        description=(
            "Growth orchestration: fetch bounded progress, result handles, and artifact handles "
            "for a previously started growth plan."
        ),
        tags={"growth", "status", "results"},
    )
    async def get_growth_plan_status(
        run_id: Annotated[str, "Run identifier returned by run_growth_plan."],
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="get_growth_plan_status", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.get_json(f"/api/v1/growth/runs/{run_id}")
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "get_growth_plan_status",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(text="Fetched growth plan status.", structured=_payload_with_source(payload))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "get_growth_plan_status",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)
