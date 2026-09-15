from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from ...cloud import CloudAPIError
from ...policy import (
    MAX_RECORDS_PER_CALL,
    bound_output,
    require_bounded_payload,
)
from ...runtime import error_result, get_telemetry, require_cloud_client
from ...telemetry import finish_tool_timing, start_tool_timing

# Match remote `src/app/tools/helpers.py` tag convention.
_UTILITY = {"utility"}

_SOURCE = {"badge": "official", "publisher": "DeepCurrent", "execution_mode": "deepcurrent-cloud"}
def register_utility_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="fetch_result_summary",
        description=(
            "Retrieve lightweight summary metadata for a stored workflow result. Do not use this for result_ids returned by "
            "execute_intelligence_package or expand_intelligence_package; use fetch_intelligence_result for those."
        ),
        tags=_UTILITY,
        meta={
            "category": "utility",
            "display_name": "Fetch Result Summary",
        },
    )
    async def fetch_result_summary(
        result_id: Annotated[str, "UUID of the stored tool result."],
    ) -> dict[str, Any]:
        """
        Return summary metadata for a previously stored orchestrator result.
        Output shape matches `deepcurrent-remote-mcp` helpers, plus a `source` field for local provenance.
        """
        timing = start_tool_timing(tool_name="fetch_result_summary", badge="official")
        telemetry = get_telemetry()
        try:
            require_bounded_payload({"result_id": result_id})
            client = require_cloud_client()
            body = await client.get_json(f"/api/v1/results/{result_id}/summary")
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "fetch_result_summary",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            if not isinstance(body, dict):
                return {
                    "status": "error",
                    "message": "Unexpected response shape for result summary.",
                    "source": _SOURCE,
                }
            return {
                "source": _SOURCE,
                "status": body.get("status", "success"),
                "result_id": result_id,
                "summary": bound_output(body.get("summary", {})),
                "artifacts": bound_output(body.get("artifacts", [])),
                "downloads": bound_output(body.get("downloads", [])),
            }
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "fetch_result_summary",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            hint = ""
            if exc.status_code == 404:
                hint = (
                    " If this result_id came from execute_intelligence_package or "
                    "expand_intelligence_package, call fetch_intelligence_result instead."
                )
            return error_result(
                status_code=exc.status_code or 0,
                message=f"Failed to fetch result summary ({exc.status_code}): {exc.message}{hint}",
                body=exc.body,
            )

    @mcp.tool(
        name="fetch_result_artifact",
        description=(
            "Retrieve a specific artifact from a stored workflow result in a streaming-friendly "
            "format. Do not use this for intelligence result_ids; use fetch_intelligence_result for those."
        ),
        tags=_UTILITY,
        meta={
            "category": "utility",
            "display_name": "Fetch Result Artifact",
        },
    )
    async def fetch_result_artifact(
        result_id: Annotated[str, "UUID of the stored tool result."],
        artifact_id: Annotated[str, "Identifier of the artifact to retrieve."],
    ) -> dict[str, Any]:
        """Return a specific artifact payload from a stored orchestrator result."""
        timing = start_tool_timing(tool_name="fetch_result_artifact", badge="official")
        telemetry = get_telemetry()
        try:
            require_bounded_payload(
                {"result_id": result_id, "artifact_id": artifact_id}
            )
            client = require_cloud_client()
            body = await client.get_json(
                f"/api/v1/results/{result_id}/artifacts/{artifact_id}",
                params={"limit": MAX_RECORDS_PER_CALL, "offset": 0},
            )
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "fetch_result_artifact",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            if not isinstance(body, dict):
                return {
                    "status": "error",
                    "message": "Unexpected response shape for artifact fetch.",
                }
            return {
                "source": _SOURCE,
                "status": "success",
                "result_id": result_id,
                "artifact": bound_output(body.get("artifact")),
            }
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "fetch_result_artifact",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(
                status_code=exc.status_code or 0,
                message=f"Failed to fetch artifact ({exc.status_code}): {exc.message}",
                body=exc.body,
            )
