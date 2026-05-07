"""Smoke test: DeepDive tools register on FastMCP without import errors."""

from __future__ import annotations


def test_register_deepdive_tools() -> None:
    from fastmcp import FastMCP

    from deepcurrent_local_mcp.plugins.official.deepdive import register_deepdive_tools

    mcp = FastMCP(name="test")
    register_deepdive_tools(mcp)
