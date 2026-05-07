from __future__ import annotations

from fastmcp import FastMCP
from smithery.decorators import smithery

from .plugins.community.byod import register_byod_tools
from .plugins.official.credits import register_credits_tools
from .plugins.official.deepdive import register_deepdive_tools
from .plugins.official.helpers import register_utility_tools
from .plugins.official.intelligence import register_intelligence_tools


@smithery.server()
def create_server() -> FastMCP:
    """
    Smithery entrypoint.

    Smithery discovers this function via:
    - pyproject.toml: [tool.smithery] server = "deepcurrent_local_mcp.smithery_server:create_server"

    Note: DeepCurrent Cloud tools require an API key at call time. BYOD tools work without it.
    """
    mcp = FastMCP(name="DeepCurrent Local MCP")
    register_credits_tools(mcp)
    register_intelligence_tools(mcp)
    register_deepdive_tools(mcp)
    register_utility_tools(mcp)
    register_byod_tools(mcp)
    return mcp
