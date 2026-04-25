from __future__ import annotations


def test_register_utility_and_crawl_tools() -> None:
    from fastmcp import FastMCP

    from deepcurrent_local_mcp.plugins.official.helpers import register_utility_tools
    from deepcurrent_local_mcp.plugins.official.website_crawl import register_website_crawl_tools

    mcp = FastMCP(name="test")
    register_utility_tools(mcp)
    register_website_crawl_tools(mcp)
