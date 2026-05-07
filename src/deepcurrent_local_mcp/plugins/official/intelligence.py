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
            "Preview available matches for people, company, investor, or wallet intelligence without charging credits. "
            "Use this before quoting when the target or desired outcome is unclear. For broad contact or intro "
            "requests, clarify who to find and whether the user wants discovery, warm intro paths, contact unlocks, or wallet identity lookup. "
            "For generic wallet-intelligence setup prompts, use this tool or ask for wallet input before quoting."
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
            "Supported package ID, including company-people-discovery-v1 for named-company people discovery. Use builder-discovery-v1 for builder, hackathon, winner, or bounty asks.",
        ],
        slots: Annotated[dict, "Slot values. Missing required slots return clarification questions."] = {},
        request_text: Annotated[
            str | None,
            "Optional raw user request text to help clarify incomplete slots.",
        ] = None,
        workflow_id: Annotated[
            str | None,
            "Optional workflow ID returned by a previous DeepCurrent response.",
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
            "Preview available matches and quote an intelligence request in one call. If there are no matches, "
            "no quote is created unless the package supports provider-neutral enrichment; use DeepDive tools for manual lead search instead. For ambiguous investor or "
            "contact requests, clarify the target and desired outcome first. For short follow-up refinements "
            "such as 'any fund' or changed result counts, pass anchor_quote_token from the previous quote so "
            "the backend preserves the prior topic. For angel or individual investor requests, prefer "
            "user-prospect-v1 unless the user explicitly asks for funds/firms. For co-investor or "
            "network-depth asks around named funds, use vc-shortlist-v1 with request_text and, when known, "
            "workflow_id='wf-investor-network-depth-v1'. For builders, developers, engineers, and hackathon "
            "participants, use builder-discovery-v1 and pass request_text so backend routing can apply "
            "general or hackathon-heavy builder matching. For wallet identity or attribution, use "
            "wallet-intelligence-v1 only with a concrete wallet address, concrete entity/label query, "
            "newline-separated wallet addresses, or parsed wallet CSV asset slots (wallet_rows/wallet_addresses). "
            "For generic prompts such as 'start wallet intelligence', call resolve_intelligence_intent or ask the user "
            "to paste wallets/upload a wallet CSV before quoting. The backend handles local lookup and external "
            "wallet intelligence enrichment under the same package. For custom result amounts, set slots.limit to the "
            "requested count. For new-results-only follow-ups, set slots.exclude_previously_delivered=true and optionally "
            "combine it with slots.limit. For expansion quotes, use parent_result_id and expansion_scope keyed by the "
            "expansion type returned in available_expansions. You MUST get explicit user confirmation before execute or expand."
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
            "Package ID to preview and quote. Use company-people-discovery-v1 first for named-company people or leadership discovery; use builder-discovery-v1 for builder, hackathon, winner, or bounty asks; use wallet-intelligence-v1 for wallet identity lookup.",
        ],
        slots: Annotated[dict, "Slot values (must satisfy required slots for quote). For wallet-intelligence-v1, include address/query, wallet_rows, wallet_addresses, or an asset_handle from a wallet CSV."],
        output_fields: Annotated[list[str], "Requested fields for the base result."] = [],
        parent_result_id: Annotated[str | None, "When quoting an expansion, provide parent_result_id."] = None,
        expansion_scope: Annotated[
            dict | None,
            "Optional expansion scope keyed by expansion type, such as {'contact_unlock': {'selection': {'mode': 'top_n', 'count': 5}, 'contact_fields': ['email']}} or {'increase_limit': {'additional': 10}}.",
        ] = None,
        request_text: Annotated[
            str | None,
            "Optional raw user request text to help refine slots before preview/quote.",
        ] = None,
        workflow_id: Annotated[
            str | None,
            "Optional workflow ID returned by a previous DeepCurrent response.",
        ] = None,
        anchor_quote_token: Annotated[
            str | None,
            "Optional quote token from the last preview/quote for short confirmations or refinements; backend preserves the prior context and merges safe refinements like limit.",
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
            if anchor_quote_token and str(anchor_quote_token).strip():
                req["anchor_quote_token"] = str(anchor_quote_token).strip()

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
                    text="Preview shows no available matches; quote not created. For manual lead search, use resolve_deepdive_outcome then quote_deepdive_plan.",
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
            "Create a quote for an already-clear intelligence request. Prefer preview_quote_intelligence_package "
            "for new requests. Pass anchor_quote_token from the prior preview/quote when the user sends a short "
            "follow-up refinement such as changing quantity or saying 'any fund', so backend preserves the prior "
            "request context. For angel or individual investor requests, prefer user-prospect-v1 unless the user "
            "explicitly asks for funds/firms. For co-investor or network-depth asks around named funds, use "
            "vc-shortlist-v1 with request_text and, when known, workflow_id='wf-investor-network-depth-v1'. "
            "For builders, developers, engineers, and hackathon participants, use builder-discovery-v1 and pass request_text "
            "so backend routing can apply general or hackathon-heavy builder matching. "
            "For wallet identity or attribution, use wallet-intelligence-v1 only with a concrete wallet address, "
            "concrete entity/label query, newline-separated wallet addresses, or parsed wallet CSV asset slots; generic wallet-intelligence setup prompts should use resolve_intelligence_intent or ask for wallet input first. "
            "For custom result amounts, set slots.limit to the requested count. For new-results-only follow-ups, set "
            "slots.exclude_previously_delivered=true and optionally combine it with slots.limit. For expansion quotes, "
            "use parent_result_id and expansion_scope keyed by the expansion type returned in available_expansions. "
            "You MUST get explicit user confirmation before execute or expand."
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
            "Package ID to quote. Use company-people-discovery-v1 first for named-company people or leadership discovery; use builder-discovery-v1 for builder, hackathon, winner, or bounty asks; use wallet-intelligence-v1 for wallet identity lookup.",
        ],
        slots: Annotated[dict, "Slot values (must satisfy required slots). For wallet-intelligence-v1, include address/query, wallet_rows, wallet_addresses, or an asset_handle from a wallet CSV."],
        output_fields: Annotated[list[str], "Output fields for base-result quotes."] = [],
        parent_result_id: Annotated[str | None, "When quoting an expansion, provide parent_result_id."] = None,
        expansion_scope: Annotated[
            dict | None,
            "Optional expansion scope keyed by expansion type, such as {'show_people_at_entity': {'selection': {'mode': 'top_n', 'count': 1}, 'people_limit': 5}}.",
        ] = None,
        request_text: Annotated[
            str | None,
            "Optional raw user request text to help refine slots before quoting.",
        ] = None,
        workflow_id: Annotated[
            str | None,
            "Optional workflow ID returned by a previous DeepCurrent response.",
        ] = None,
        anchor_quote_token: Annotated[
            str | None,
            "Optional quote token from the last preview/quote for short confirmations or refinements; backend preserves the prior context and merges safe refinements like limit.",
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
        description="Run an approved intelligence discovery request. Only use after explicit user confirmation of the quote.",
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
        output_fields: Annotated[list[str], "Output fields that must match the quote payload."],
        quote_token: Annotated[str, "Quote token returned by quote_intelligence_package."],
        workflow_id: Annotated[
            str | None,
            "Optional workflow ID returned by quote/preview. Pass it through when present so execute matches the quoted workflow.",
        ] = None,
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
                    "workflow_id": workflow_id,
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
            "Fetch a saved intelligence result by result_id. Use this for result_ids returned by "
            "execute_intelligence_package or expand_intelligence_package. Do not use "
            "fetch_result_summary for these intelligence result_ids. "
            "Use when the user wants the saved result inspected in chat; records are truncated to keep responses manageable."
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
            "Unlock more details or increase the result limit for an existing intelligence result. "
            "Use after the user has reviewed a base result and explicitly approved the expansion quote. "
            "Use the expansion type returned in available_expansions; common types include contact_unlock, "
            "network_depth, increase_limit, show_people_at_entity, show_people_at_person_company, "
            "show_company_or_fund_context, show_investor_network_context, show_investors_for_company, "
            "show_portfolio_companies_for_investor, and wallet_activity_snapshot."
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
        expansion_type: Annotated[
            str,
            "Expansion type returned by available_expansions, for example contact_unlock, increase_limit, show_people_at_entity, show_investors_for_company, or wallet_activity_snapshot.",
        ],
        expansion_params: Annotated[
            dict,
            "Expansion parameters for expansion_type. Examples: {'additional': 10}, {'selection': {'mode': 'top_n', 'count': 5}, 'contact_fields': ['email']}, or {'selection': {'mode': 'explicit_ids', 'ids': ['...']}}.",
        ] = {},
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
