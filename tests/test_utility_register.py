from __future__ import annotations

import pytest


def test_register_utility_tools() -> None:
    from fastmcp import FastMCP

    from deepcurrent_local_mcp.plugins.official.helpers import register_utility_tools

    mcp = FastMCP(name="test")
    register_utility_tools(mcp)


@pytest.mark.anyio
async def test_utility_tools_reject_oversized_identifiers_before_cloud_access() -> None:
    from fastmcp import FastMCP

    from deepcurrent_local_mcp.plugins.official.helpers import register_utility_tools

    mcp = FastMCP(name="test")
    register_utility_tools(mcp)

    summary = await mcp._tool_manager._tools["fetch_result_summary"].fn(
        result_id="r" * 50_001
    )
    artifact = await mcp._tool_manager._tools["fetch_result_artifact"].fn(
        result_id="result",
        artifact_id="a" * 50_001,
    )

    assert summary["error"]["code"] == "mcp_request_limit_exceeded"
    assert artifact["error"]["code"] == "mcp_request_limit_exceeded"
