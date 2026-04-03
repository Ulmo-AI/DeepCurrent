from __future__ import annotations

from typing import Any

from . import __version__
from .cloud import CloudAPIError, DeepCurrentCloudClient
from .config import load_config
from .telemetry import TelemetryClient


_cloud_client: DeepCurrentCloudClient | None = None
_telemetry: TelemetryClient | None = None


def get_cloud_client() -> DeepCurrentCloudClient | None:
    global _cloud_client
    if _cloud_client is not None:
        return _cloud_client

    cfg = load_config()
    if not cfg.api_key:
        return None

    _cloud_client = DeepCurrentCloudClient(base_url=cfg.api_url, api_key=cfg.api_key)
    return _cloud_client


def require_cloud_client() -> DeepCurrentCloudClient:
    """
    Official (cloud-backed) plugins can call this at tool execution time.

    Important: the daemon must still boot and serve BYOD/community tools even if the
    user has no DeepCurrent account or API key configured.
    """
    client = get_cloud_client()
    if client is None:
        raise CloudAPIError(status_code=401, message="Missing DEEPCURRENT_API_KEY", body=None)
    return client


def get_telemetry() -> TelemetryClient:
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryClient.from_env(app="deepcurrent-local-mcp", version=__version__)
    return _telemetry


def ok_result(*, text: str, structured: dict[str, Any]) -> dict[str, Any]:
    # Keep "structured" fields at the top-level so clients can access
    # keys like quote_token / credits without extra nesting.
    return {"ok": True, "text": text, **(structured or {})}


def error_result(*, status_code: int, message: str, body: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"status_code": status_code, "message": message}
    if body is not None:
        payload["body"] = body
    return {"ok": False, "text": message, "error": payload}

