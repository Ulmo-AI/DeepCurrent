from __future__ import annotations


def test_register_utility_tools() -> None:
    from fastmcp import FastMCP

    from deepcurrent_local_mcp.plugins.official.helpers import register_utility_tools

    mcp = FastMCP(name="test")
    register_utility_tools(mcp)
