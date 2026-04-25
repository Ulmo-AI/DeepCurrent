"""
Assert the FastMCP server exposes the full Phase-15-expected tool surface (names only, no network).
"""

from __future__ import annotations

import asyncio

from fastmcp import FastMCP

# Keep in sync with PRD §12.6 and README "Tool surface (current)".
EXPECTED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "connect_deepcurrent_cloud",
        "get_credit_status",
        "claim_growth_credits",
        "resolve_intelligence_intent",
        "preview_quote_intelligence_package",
        "quote_intelligence_package",
        "execute_intelligence_package",
        "fetch_intelligence_result",
        "expand_intelligence_package",
        "resolve_growth_outcome",
        "quote_growth_plan",
        "run_growth_plan",
        "get_growth_plan_status",
        "fetch_result_summary",
        "fetch_result_artifact",
        "get_website_crawl_cost",
        "list_byod_connectors",
        "run_byod_connector",
    }
)


def _get_tool_names(mcp: FastMCP) -> list[str]:

    async def _load() -> list[str]:
        tools = await mcp.get_tools()
        if isinstance(tools, dict):
            return list(tools.keys())
        out: list[str] = []
        for t in tools:
            n = getattr(t, "name", None)
            if isinstance(n, str):
                out.append(n)
        return out

    return list(asyncio.run(_load()))


def test_main_mcp_exposes_all_expected_tool_names() -> None:
    from deepcurrent_local_mcp.main import mcp

    names = set(_get_tool_names(mcp))
    missing = EXPECTED_TOOL_NAMES - names
    extra = names - EXPECTED_TOOL_NAMES
    assert not missing, f"Missing tool names: {sorted(missing)}"
    assert not extra, f"Unexpected extra tool names: {sorted(extra)}"


def test_smithery_server_exposes_all_expected_tool_names() -> None:
    from deepcurrent_local_mcp.smithery_server import create_server

    mcp = create_server()
    names = set(_get_tool_names(mcp))
    missing = EXPECTED_TOOL_NAMES - names
    assert not missing, f"Missing tool names: {sorted(missing)}"
    # Smithery is the same surface as main; extras would be a harness bug.
    extra = names - EXPECTED_TOOL_NAMES
    assert not extra, f"Unexpected extra tool names: {sorted(extra)}"
