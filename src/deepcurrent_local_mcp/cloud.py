from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class CloudAPIError(Exception):
    status_code: int
    message: str
    body: Any | None = None

    def __str__(self) -> str:  # pragma: no cover
        return f"DeepCurrent Cloud error ({self.status_code}): {self.message}"


class DeepCurrentCloudClient:
    def __init__(self, *, base_url: str, api_key: str, timeout_s: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_s)

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            resp = await self._client.request(
                method=method.upper(),
                url=path,
                headers=self._headers(),
                json=json_body,
                params=params,
            )
        except httpx.RequestError as exc:
            raise CloudAPIError(status_code=0, message=f"Network error: {exc.__class__.__name__}") from exc

        if resp.status_code >= 400:
            message = resp.text.strip() or resp.reason_phrase
            body: Any | None = None
            try:
                body = resp.json()
                # FastAPI style errors commonly include {"detail": "..."}.
                if isinstance(body, dict) and isinstance(body.get("detail"), str):
                    message = body["detail"]
            except Exception:
                body = None
            raise CloudAPIError(status_code=resp.status_code, message=message, body=body)

        # Prefer JSON, but don't crash if the API returns empty bodies.
        if not resp.content:
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text

    async def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self.request_json("GET", path, params=params)

    async def post_json(self, path: str, *, json_body: dict[str, Any] | None = None) -> Any:
        return await self.request_json("POST", path, json_body=json_body)

