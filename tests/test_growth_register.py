"""Smoke test: growth tools register on FastMCP without import errors."""

from __future__ import annotations


def test_register_growth_tools() -> None:
    from fastmcp import FastMCP

    from deepcurrent_local_mcp.plugins.official.growth import register_growth_tools

    mcp = FastMCP(name="test")
    register_growth_tools(mcp)
