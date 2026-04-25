from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from ...cloud import CloudAPIError
from ...runtime import error_result, get_telemetry, ok_result, require_cloud_client
from ...telemetry import finish_tool_timing, start_tool_timing

_SOURCE = {"badge": "official", "publisher": "DeepCurrent", "execution_mode": "deepcurrent-cloud"}


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def _payload_with_source(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {"source": _SOURCE, **payload}
    return {"source": _SOURCE, "payload": payload}


def register_website_crawl_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="get_website_crawl_cost",
        description=(
            "Estimate the credit cost for crawling one or more websites. Show the estimated cost and get "
            "explicit user approval before running any paid crawl."
        ),
        tags={"crawling", "cost-estimation"},
    )
    async def get_website_crawl_cost(
        start_urls: Annotated[
            list[str],
            "A list of one or more URLs to use as the starting point for the crawl.",
        ],
        max_crawl_pages: Annotated[
            int,
            "The maximum number of pages to crawl. Ask the user before choosing a value.",
        ],
    ) -> dict[str, Any]:
        timing = start_tool_timing(tool_name="get_website_crawl_cost", badge="official")
        telemetry = get_telemetry()
        try:
            client = require_cloud_client()
            normalized_urls = [_normalize_url(u) for u in start_urls]
            cost_payload: dict[str, Any] = {
                "automation_id": "deepcurrent/website-crawler-v1",
                "input_data": {
                    "startUrls": [{"url": url} for url in normalized_urls],
                    "maxCrawlPages": max_crawl_pages,
                },
            }
            result = await client.post_json(
                "/api/v1/automations/website-crawler/cost",
                json_body=cost_payload,
            )
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "get_website_crawl_cost",
                    "badge": "official",
                    "status": "success",
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            if isinstance(result, dict):
                return ok_result(
                    text="Crawl cost estimated.",
                    structured=_payload_with_source(result),
                )
            return ok_result(text="Crawl cost estimated.", structured=_payload_with_source({"value": result}))
        except CloudAPIError as exc:
            telemetry.capture_background(
                event="tool_executed",
                properties={
                    "tool_name": "get_website_crawl_cost",
                    "badge": "official",
                    "status": "error",
                    "http_status": exc.status_code,
                    "latency_ms": finish_tool_timing(timing),
                },
            )
            return error_result(status_code=exc.status_code or 0, message=exc.message, body=exc.body)
