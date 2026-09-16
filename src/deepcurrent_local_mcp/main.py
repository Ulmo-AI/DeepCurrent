from __future__ import annotations

import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from . import __version__
from .plugins.community.byod import register_byod_tools
from .plugins.official.credits import register_credits_tools
from .plugins.official.deepdive import register_deepdive_tools
from .plugins.official.helpers import register_utility_tools
from .plugins.official.intelligence import register_intelligence_tools
from .plugins.official.lead_search import register_lead_search_tools
from .runtime import get_telemetry


MCP_SERVER_NAME = "DeepCurrent Local MCP"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _validated_http_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized not in _LOOPBACK_HOSTS:
        raise ValueError(
            "Local MCP HTTP transport must bind to a loopback host "
            "(127.0.0.1, localhost, or ::1)."
        )
    return normalized

# Expose an MCP instance for `fastmcp run` style entrypoints.
mcp = FastMCP(name=MCP_SERVER_NAME, version=__version__)
register_credits_tools(mcp)
register_intelligence_tools(mcp)
register_lead_search_tools(mcp)
register_deepdive_tools(mcp)
register_utility_tools(mcp)
register_byod_tools(mcp)


def main() -> None:
    # Optional: load .env for local dev. Most MCP clients should set env vars explicitly.
    load_dotenv(override=False)

    # Telemetry is enabled by default (opt-out via DEEPCURRENT_TELEMETRY=0).
    # This emits metadata-only signals (no tool inputs/outputs, no API keys).
    get_telemetry().capture_background(
        event="daemon_started",
        properties={
            "transport": (os.getenv("DEEPCURRENT_MCP_TRANSPORT") or "stdio").strip().lower(),
        },
    )

    transport = (os.getenv("DEEPCURRENT_MCP_TRANSPORT") or "stdio").strip().lower()
    if transport == "http":
        host = _validated_http_host(
            os.getenv("DEEPCURRENT_MCP_HTTP_HOST") or "127.0.0.1"
        )
        port = int(os.getenv("DEEPCURRENT_MCP_HTTP_PORT") or "8009")
        path = (os.getenv("DEEPCURRENT_MCP_HTTP_PATH") or "/mcp").strip() or "/mcp"
        mcp.run(transport="http", host=host, port=port, path=path)
        return

    # Default: STDIO transport for local MCP clients.
    mcp.run(transport="stdio")
