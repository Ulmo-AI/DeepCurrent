from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ...cloud import CloudAPIError
from ...config import load_config
from ...runtime import error_result, get_telemetry, ok_result, require_cloud_client
from ...telemetry import finish_tool_timing, start_tool_timing


_SOURCE = {"badge": "official", "publisher": "DeepCurrent", "execution_mode": "deepcurrent-cloud"}


def register_credits_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="connect_deepcurrent_cloud",
        description="Check that your DeepCurrent credentials work and return current plan and credit details.",
        tags={"deepcurrent", "official", "auth", "credits"},
    )
    async def connect_deepcurrent_cloud() -> dict[str, Any]:
        timing = start_tool_timing(tool_name="connect_deepcurrent_cloud", badge="official")
        telemetry = get_telemetry()
        cfg = load_config()
        key_last4 = (cfg.api_key or "")[-4:] if cfg.api_key else None

        try:
            client = require_cloud_client()

            # Validate API key (but do not return PII-rich user payload to model context).
            _ = await client.get_json("/api/v1/users/me")
            status = await client.get_json("/api/v1/subscriptions/status")

            tier = (status or {}).get("tier")
            sub_status = (status or {}).get("status")
            credits_total = (status or {}).get("credits_total")
            credits_expiring = (status or {}).get("credits_expiring")

            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "connect_deepcurrent_cloud",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return ok_result(
                text=f"Connected. tier={tier} status={sub_status} credits_total={credits_total}",
                structured={
                    "source": _SOURCE,
                    "status": "connected",
                    "auth_type": "api_key",
                    "api_url": cfg.api_url,
                    "api_key_last_four": key_last4,
                    "tier": tier,
                    "subscription_status": sub_status,
                    "credits_total": credits_total,
                    "credits_expiring": credits_expiring,
                },
            )
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "connect_deepcurrent_cloud",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="get_credit_status",
        description="Fetch the current plan, subscription status, and credit balance.",
        tags={"deepcurrent", "official", "credits"},
    )
    async def get_credit_status() -> dict[str, Any]:
        timing = start_tool_timing(tool_name="get_credit_status", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            status = await client.get_json("/api/v1/subscriptions/status")
            quests: dict | None = None
            try:
                q = await client.get_json("/api/v1/quests/status")
                if isinstance(q, dict):
                    quests = q
            except CloudAPIError:
                pass
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "get_credit_status",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            if isinstance(status, dict):
                structured = {"source": _SOURCE, **status}
                if quests is not None:
                    structured["quests"] = quests
            else:
                structured = {"source": _SOURCE, "credit_status": status}
                if quests is not None:
                    structured["quests"] = quests
            return ok_result(text="Fetched credit status.", structured=structured)
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "get_credit_status",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

    @mcp.tool(
        name="claim_growth_credits",
        description="Claim any available promotional growth credits.",
        tags={"deepcurrent", "official", "credits", "faucet"},
    )
    async def claim_growth_credits() -> dict[str, Any]:
        timing = start_tool_timing(tool_name="claim_growth_credits", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            payload = await client.post_json("/api/v1/subscriptions/faucet/claim", json_body={})
            message = str((payload or {}).get("message") or "Claim attempted.")

            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "claim_growth_credits",
                    "badge": "official",
                    "status": "success",
                    "http_status": 200,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            if isinstance(payload, dict):
                structured = {"source": _SOURCE, "http_status": 200, **payload}
            else:
                structured = {"source": _SOURCE, "http_status": 200, "payload": payload}
            return ok_result(text=message, structured=structured)
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "claim_growth_credits",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )

            # Backend returns FaucetClaimResponse bodies even for 403/409; normalize into a deterministic state.
            if exc.status_code in (403, 409) and isinstance(exc.body, dict):
                return ok_result(
                    text=str(exc.body.get("message") or exc.message),
                    structured={"source": _SOURCE, "http_status": exc.status_code, **exc.body},
                )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)

