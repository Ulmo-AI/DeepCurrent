from __future__ import annotations

import httpx
import pytest

from deepcurrent_local_mcp.cloud import CloudAPIError, DeepCurrentCloudClient


@pytest.mark.asyncio
async def test_structured_backend_error_keeps_code_and_reset_metadata() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "42", "X-Request-ID": "req-123"},
            json={
                "detail": {
                    "code": "distinct_record_limit_reached",
                    "message": "Upgrade to continue.",
                    "resets_at": "2026-10-01T00:00:00Z",
                }
            },
            request=request,
        )

    client = DeepCurrentCloudClient(base_url="https://api.example.test", api_key="test")
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.example.test")

    with pytest.raises(CloudAPIError) as exc_info:
        await client.get_json("/api/v1/results")

    exc = exc_info.value
    assert exc.message == "Upgrade to continue."
    assert exc.code == "distinct_record_limit_reached"
    assert exc.retry_after_seconds == 42
    assert exc.request_id == "req-123"
    assert exc.body == {
        "detail": {
            "code": "distinct_record_limit_reached",
            "message": "Upgrade to continue.",
            "resets_at": "2026-10-01T00:00:00Z",
        },
        "_transport": {
            "code": "distinct_record_limit_reached",
            "retry_after_seconds": 42,
            "request_id": "req-123",
        },
    }
    await client._client.aclose()
