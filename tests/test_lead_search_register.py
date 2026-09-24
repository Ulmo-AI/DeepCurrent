from __future__ import annotations

from typing import Any

import pytest
from fastmcp import FastMCP

from deepcurrent_local_mcp.plugins.official.lead_search import (
    register_lead_search_tools,
)


class FakeCloudClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: dict[tuple[str, str], Any] = {}

    async def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        self.calls.append({"method": "GET", "path": path, "payload": params})
        return self.responses[("GET", path)]

    async def post_json(self, path: str, *, json_body: dict[str, Any] | None = None) -> Any:
        self.calls.append({"method": "POST", "path": path, "payload": json_body})
        return self.responses[("POST", path)]

    async def delete_json(self, path: str) -> Any:
        self.calls.append({"method": "DELETE", "path": path, "payload": None})
        return self.responses[("DELETE", path)]


async def _run_tool(mcp: FastMCP, name: str, arguments: dict):
    tool = await mcp.get_tool(name)
    assert tool is not None
    structured = (await tool.run(arguments)).structured_content
    return structured.get("result", structured)


@pytest.mark.anyio
async def test_search_leads_maps_funds_and_uses_bounded_backend_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeCloudClient()
    client.responses[("POST", "/api/v1/lead-search/search")] = {
        "context": "investors",
        "items": [{"id": "fund-1", "name": "Example Fund"}],
        "total": 51,
        "limit": 25,
        "offset": 25,
        "has_more": True,
        "query_ms": 4,
        "access_policy": {"plan": "pro", "page_size": 25, "current_page": 2, "max_pages": 20},
    }
    monkeypatch.setattr("deepcurrent_local_mcp.plugins.official.lead_search.require_cloud_client", lambda: client)
    mcp = FastMCP(name="test")
    register_lead_search_tools(mcp)

    result = await _run_tool(mcp, "search_leads", {"context": "funds", "query": "web3", "page": 2, "page_size": 25})

    assert result["ok"] is True
    assert result["context"] == "funds"
    assert result["next_page"] == 3
    assert client.calls[-1]["payload"] == {
        "context": "investors",
        "query": "web3",
        "filters": {},
        "sort": None,
        "limit": 25,
        "offset": 25,
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("requested_context", "api_context"),
    [
        ("people", "people"),
        ("companies", "companies"),
        ("funds", "investors"),
        ("wallets", "wallets"),
    ],
)
async def test_search_leads_preserves_rich_rows_for_every_context(
    monkeypatch: pytest.MonkeyPatch,
    requested_context: str,
    api_context: str,
) -> None:
    client = FakeCloudClient()
    client.responses[("POST", "/api/v1/lead-search/search")] = {
        "context": api_context,
        "items": [
            {
                "id": f"{api_context}-1",
                "context": api_context,
                "name": "Example",
                "description": "Public description",
                "fields": {"website": "https://example.com", "followers": 42},
                "channels": ["Website", "X"],
                "public_profiles": [
                    {"channel": "Website", "url": "https://example.com"}
                ],
                "match_reasons": [{"kind": "query", "label": "Name match"}],
            }
        ],
        "total": 1,
        "limit": 25,
        "offset": 0,
        "has_more": False,
        "query_ms": 2,
    }
    monkeypatch.setattr(
        "deepcurrent_local_mcp.plugins.official.lead_search.require_cloud_client",
        lambda: client,
    )
    mcp = FastMCP(name="test")
    register_lead_search_tools(mcp)

    result = await _run_tool(
        mcp,
        "search_leads",
        {"context": requested_context, "query": "Example"},
    )

    item = result["items"][0]
    assert result["context"] == requested_context
    assert item["context"] == requested_context
    assert item["description"] == "Public description"
    assert item["fields"]["followers"] == 42
    assert item["public_profiles"] == [
        {"channel": "Website", "url": "https://example.com"}
    ]


@pytest.mark.anyio
async def test_saved_search_tools_call_cloud_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeCloudClient()
    saved_id = "00000000-0000-0000-0000-000000000001"
    saved_fund = {
        "id": saved_id,
        "name": "Web3 funds",
        "search": {"context": "investors", "query": "web3", "filters": {}, "sort": "relevance", "limit": 25, "offset": 0},
    }
    saved_person = {
        **saved_fund,
        "name": "Founders",
        "search": {"context": "people", "query": "", "filters": {"role": ["Founders"]}, "sort": "relevance", "limit": 25, "offset": 0},
    }
    client.responses[("GET", "/api/v1/lead-search/saved-searches")] = [saved_fund]
    client.responses[("POST", "/api/v1/lead-search/saved-searches")] = saved_person
    client.responses[("DELETE", f"/api/v1/lead-search/saved-searches/{saved_id}")] = None
    monkeypatch.setattr("deepcurrent_local_mcp.plugins.official.lead_search.require_cloud_client", lambda: client)
    mcp = FastMCP(name="test")
    register_lead_search_tools(mcp)

    listed = await _run_tool(mcp, "list_saved_searches", {"limit": 25, "offset": 0})
    created = await _run_tool(mcp, "save_lead_search", {"name": "Founders", "context": "people", "filters": {"role": ["Founders"]}})
    deleted = await _run_tool(mcp, "delete_saved_search", {"saved_search_id": saved_id})

    assert listed["saved_searches"][0]["search"]["context"] == "funds"
    assert created["saved_search"]["id"] == saved_id
    assert deleted["deleted_saved_search_id"] == saved_id
