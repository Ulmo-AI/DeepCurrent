from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ...cloud import CloudAPIError
from ...policy import bound_output, require_bounded_payload
from ...runtime import require_cloud_client

_SOURCE = {"badge": "official", "publisher": "DeepCurrent", "execution_mode": "deepcurrent-cloud"}
_TO_API = {"people": "people", "companies": "companies", "funds": "investors", "wallets": "wallets"}
_FROM_API = {value: key for key, value in _TO_API.items()}
LeadContext = Literal["people", "companies", "funds", "wallets"]


class SourceInfo(BaseModel):
    badge: Literal["official"] = "official"
    publisher: Literal["DeepCurrent"] = "DeepCurrent"
    execution_mode: Literal["deepcurrent-cloud"] = "deepcurrent-cloud"


class ErrorDetails(BaseModel):
    type: str
    status_code: int | None = None
    message: str
    code: str | None = None
    retry_after_seconds: int | None = None
    request_id: str | None = None
    suggested_next_action: str | None = None
    body: Any | None = None


class LeadSearchFilterOption(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: str
    label: str
    category: str | None = None


class LeadSearchFilterDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    label: str
    options: list[LeadSearchFilterOption] = Field(default_factory=list)
    searchable: bool = False
    kind: str = "multi_select"
    selection_mode: str = "multiple"
    group: str = "Other"
    advanced: bool = False
    hidden: bool = False
    default_open: bool = False
    description: str | None = None
    unit: str | None = None


class LeadSearchSortDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    label: str


class LeadSearchContextMeta(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: LeadContext
    label: str
    description: str
    available: bool
    filters: list[LeadSearchFilterDefinition] = Field(default_factory=list)
    sorts: list[LeadSearchSortDefinition] = Field(default_factory=list)


class LeadSearchPublicProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    channel: str
    url: str


class LeadSearchContactAccess(BaseModel):
    model_config = ConfigDict(extra="allow")
    group: str
    status: str
    credits: int
    values: dict[str, Any] = Field(default_factory=dict)
    verification_status: str | None = None


class LeadSearchMatchReason(BaseModel):
    model_config = ConfigDict(extra="allow")
    kind: str
    label: str
    source: str | None = None


class LeadSearchItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    context: LeadContext
    name: str
    subtitle: str | None = None
    description: str | None = None
    fields: dict[str, str | int | float | list[str] | None] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=list)
    public_profiles: list[LeadSearchPublicProfile] = Field(default_factory=list)
    contact_access: list[LeadSearchContactAccess] = Field(default_factory=list)
    match_reasons: list[LeadSearchMatchReason] = Field(default_factory=list)
    is_saved: bool = False


class LeadSearchAccessPolicy(BaseModel):
    model_config = ConfigDict(extra="allow")
    plan: str
    page_size: int
    current_page: int
    max_pages: int
    distinct_record_remaining: int | None = None
    resets_at: str | None = None


class SavedSearchRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    context: LeadContext
    query: str = ""
    filters: dict[str, list[str]] = Field(default_factory=dict)
    sort: str | None = None
    limit: int = 25
    offset: int = 0


class SavedSearch(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    search: SavedSearchRequest
    created_at: str | None = None
    updated_at: str | None = None


class ToolFailure(BaseModel):
    ok: Literal[False] = False
    text: str
    source: SourceInfo = Field(default_factory=SourceInfo)
    error: ErrorDetails


class CapabilitiesResult(BaseModel):
    ok: Literal[True] = True
    text: str
    source: SourceInfo = Field(default_factory=SourceInfo)
    server_version: str = "0.2.0"
    product_contract_revision: str = "lead-search-v1"
    tier: str | None = None
    subscription_status: str | None = None
    credits_total: int | None = None
    lead_search_contexts: list[LeadSearchContextMeta] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class LeadSearchSchemaResult(BaseModel):
    ok: Literal[True] = True
    text: str
    source: SourceInfo = Field(default_factory=SourceInfo)
    contexts: list[LeadSearchContextMeta] = Field(default_factory=list)


class LeadSearchResult(BaseModel):
    ok: Literal[True] = True
    text: str
    source: SourceInfo = Field(default_factory=SourceInfo)
    context: LeadContext
    items: list[LeadSearchItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    has_more: bool
    next_page: int | None = None
    query_ms: int | None = None
    access_policy: LeadSearchAccessPolicy | None = None


class SavedSearchesResult(BaseModel):
    ok: Literal[True] = True
    text: str
    source: SourceInfo = Field(default_factory=SourceInfo)
    saved_searches: list[SavedSearch] = Field(default_factory=list)
    limit: int
    offset: int


class SavedSearchResult(BaseModel):
    ok: Literal[True] = True
    text: str
    source: SourceInfo = Field(default_factory=SourceInfo)
    saved_search: SavedSearch


class DeleteSavedSearchResult(BaseModel):
    ok: Literal[True] = True
    text: str = "Deleted saved search."
    source: SourceInfo = Field(default_factory=SourceInfo)
    deleted_saved_search_id: str


def _failure(exc: CloudAPIError, fallback: str) -> ToolFailure:
    return ToolFailure(
        text=exc.message or fallback,
        error={
            "type": "quota_or_rate_limit" if exc.status_code == 429 else "api_error",
            "status_code": exc.status_code,
            "message": exc.message or fallback,
            "body": exc.body,
            "code": exc.code,
            "retry_after_seconds": exc.retry_after_seconds,
            "request_id": exc.request_id,
            "suggested_next_action": (
                exc.body.get("detail", {}).get("suggested_next_action")
                if isinstance(exc.body, dict)
                and isinstance(exc.body.get("detail"), dict)
                else None
            ),
        },
    )


async def _request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    fallback: str,
) -> Any | ToolFailure:
    try:
        client = require_cloud_client()
        if method == "GET":
            return await client.get_json(path, params=params)
        if method == "POST":
            return await client.post_json(path, json_body=payload)
        return await client.delete_json(path)
    except CloudAPIError as exc:
        return _failure(exc, fallback)


def _contexts(meta: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        {**context, "id": _FROM_API.get(context.get("id"), context.get("id"))}
        for context in (meta or {}).get("contexts", [])
    ]


def _map_item_contexts(
    items: list[dict[str, Any]], default_context: LeadContext
) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "context": _FROM_API.get(
                item.get("context"), item.get("context") or default_context
            ),
        }
        for item in items
    ]


def _map_saved_searches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for row in rows:
        search = row.get("search")
        mapped_search = (
            {**search, "context": _FROM_API.get(search.get("context"), search.get("context"))}
            if isinstance(search, dict)
            else search
        )
        mapped.append({**row, "search": mapped_search})
    return mapped


def register_lead_search_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="get_deepcurrent_capabilities",
        description="Inspect the current DeepCurrent account and discover the supported Lead Search contexts before choosing a workflow.",
        tags={"deepcurrent", "official", "discovery"},
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def get_deepcurrent_capabilities() -> CapabilitiesResult | ToolFailure:
        user = await _request("GET", "/api/v1/users/me", fallback="Could not inspect the account.")
        if isinstance(user, ToolFailure):
            return user
        status = await _request("GET", "/api/v1/subscriptions/status", fallback="Could not inspect the subscription.")
        if isinstance(status, ToolFailure):
            return status
        meta = await _request("GET", "/api/v1/lead-search/meta", fallback="Could not load Lead Search capabilities.")
        if isinstance(meta, ToolFailure):
            return meta
        official_tools = sorted(
            tool.name
            for tool in await mcp.list_tools()
            if tool.name not in {"list_byod_connectors", "run_byod_connector"}
        )
        return CapabilitiesResult(
            text="Fetched DeepCurrent capabilities.",
            tier=(status or {}).get("tier") or (user or {}).get("subscription_tier"),
            subscription_status=(status or {}).get("status") or (user or {}).get("subscription_status"),
            credits_total=(status or {}).get("credits_total"),
            lead_search_contexts=_contexts(meta),
            tools=official_tools,
        )

    @mcp.tool(
        name="get_lead_search_schema",
        description="Return the current filters and sort options for People, Companies, Funds, and Wallet Lead Search.",
        tags={"deepcurrent", "official", "lead-search", "schema"},
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def get_lead_search_schema() -> LeadSearchSchemaResult | ToolFailure:
        meta = await _request("GET", "/api/v1/lead-search/meta", fallback="Could not load Lead Search schema.")
        if isinstance(meta, ToolFailure):
            return meta
        return LeadSearchSchemaResult(text="Fetched Lead Search schema.", contexts=_contexts(meta))

    @mcp.tool(
        name="search_leads",
        description="Search DeepCurrent People, Companies, Funds, or Wallets. Call get_lead_search_schema first when filter IDs or sort options are unknown.",
        tags={"deepcurrent", "official", "lead-search"},
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def search_leads(
        context: Annotated[LeadContext, Field(description="Result type to search.")],
        query: Annotated[str, Field(max_length=120)] = "",
        filters: Annotated[dict[str, list[str]] | None, Field(description="Filter IDs and values from get_lead_search_schema.")] = None,
        sort: str | None = None,
        page: Annotated[int, Field(ge=1)] = 1,
        page_size: Annotated[int, Field(ge=1, le=25)] = 25,
    ) -> LeadSearchResult | ToolFailure:
        payload = {"context": _TO_API[context], "query": query.strip(), "filters": filters or {}, "sort": sort, "limit": page_size, "offset": (page - 1) * page_size}
        require_bounded_payload(payload)
        body = await _request("POST", "/api/v1/lead-search/search", payload=payload, fallback="Lead Search failed.")
        if isinstance(body, ToolFailure):
            return body
        result_context = _FROM_API.get(body.get("context", payload["context"]), context)
        items = bound_output(
            _map_item_contexts(body.get("items") or [], result_context)
        )
        has_more = bool(body.get("has_more"))
        return LeadSearchResult(
            text=f"Found {body.get('total', 0)} {result_context} results; returned {len(items)}.",
            context=result_context,
            items=items,
            total=int(body.get("total", 0)),
            page=page,
            page_size=int(body.get("limit", page_size)),
            has_more=has_more,
            next_page=page + 1 if has_more else None,
            query_ms=body.get("query_ms"),
            access_policy=body.get("access_policy"),
        )

    @mcp.tool(
        name="list_saved_searches",
        description="List the current account's saved Lead Searches.",
        tags={"deepcurrent", "official", "lead-search", "saved-searches"},
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_saved_searches(
        limit: Annotated[int, Field(ge=1, le=25)] = 25,
        offset: Annotated[int, Field(ge=0, le=10_000)] = 0,
    ) -> SavedSearchesResult | ToolFailure:
        body = await _request("GET", "/api/v1/lead-search/saved-searches", params={"limit": limit, "offset": offset}, fallback="Could not list saved searches.")
        if isinstance(body, ToolFailure):
            return body
        saved_searches = _map_saved_searches(body or [])
        return SavedSearchesResult(text=f"Fetched {len(saved_searches)} saved searches.", saved_searches=bound_output(saved_searches), limit=limit, offset=offset)

    @mcp.tool(
        name="save_lead_search",
        description="Save a Lead Search to the current DeepCurrent account.",
        tags={"deepcurrent", "official", "lead-search", "saved-searches"},
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def save_lead_search(
        name: Annotated[str, Field(min_length=2, max_length=255)],
        context: LeadContext,
        query: Annotated[str, Field(max_length=120)] = "",
        filters: dict[str, list[str]] | None = None,
        sort: str | None = None,
    ) -> SavedSearchResult | ToolFailure:
        payload = {"name": name.strip(), "search": {"context": _TO_API[context], "query": query.strip(), "filters": filters or {}, "sort": sort, "limit": 25, "offset": 0}}
        require_bounded_payload(payload)
        body = await _request("POST", "/api/v1/lead-search/saved-searches", payload=payload, fallback="Could not save the search.")
        if isinstance(body, ToolFailure):
            return body
        search = body.get("search") if isinstance(body, dict) else None
        if isinstance(search, dict):
            search["context"] = _FROM_API.get(search.get("context"), search.get("context"))
        return SavedSearchResult(text=f"Saved search {body.get('name', name)}.", saved_search=body)

    @mcp.tool(
        name="delete_saved_search",
        description="Delete one saved Lead Search owned by the current DeepCurrent account.",
        tags={"deepcurrent", "official", "lead-search", "saved-searches"},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def delete_saved_search(
        saved_search_id: Annotated[str, Field(pattern=r"^[0-9a-fA-F-]{36}$")],
    ) -> DeleteSavedSearchResult | ToolFailure:
        body = await _request("DELETE", f"/api/v1/lead-search/saved-searches/{saved_search_id}", fallback="Could not delete the saved search.")
        if isinstance(body, ToolFailure):
            return body
        return DeleteSavedSearchResult(deleted_saved_search_id=saved_search_id)
