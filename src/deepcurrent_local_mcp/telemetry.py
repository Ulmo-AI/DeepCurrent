from __future__ import annotations

import asyncio
import os
import platform
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


DEFAULT_TELEMETRY_ENDPOINT = "https://api.deepcurrent.app/api/v1/telemetry/events"


def _env_flag(name: str, *, default: str) -> bool:
    raw = (os.getenv(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TelemetryContext:
    app: str
    version: str
    session_id: str


class TelemetryClient:
    """
    Minimal, "spyware-free" telemetry:
    - enabled by default (opt-out via DEEPCURRENT_TELEMETRY=0)
    - sends metadata only (no tool inputs/outputs, no API keys)
    - failures are swallowed (never break tool execution)
    """

    def __init__(
        self,
        *,
        endpoint: str,
        enabled: bool,
        context: TelemetryContext,
        timeout_s: float = 3.0,
    ) -> None:
        self._enabled = enabled
        self._endpoint = (endpoint or "").strip()
        self._context = context
        self._timeout_s = timeout_s
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_env(cls, *, app: str, version: str) -> "TelemetryClient":
        enabled = _env_flag("DEEPCURRENT_TELEMETRY", default="1")
        endpoint = os.getenv("DEEPCURRENT_TELEMETRY_ENDPOINT", DEFAULT_TELEMETRY_ENDPOINT)
        try:
            timeout_s = float(os.getenv("DEEPCURRENT_TELEMETRY_TIMEOUT_S") or "3.0")
        except (TypeError, ValueError):
            timeout_s = 3.0
        timeout_s = max(0.5, min(timeout_s, 10.0))

        context = TelemetryContext(app=app, version=version, session_id=uuid.uuid4().hex)
        return cls(endpoint=endpoint, enabled=enabled, context=context, timeout_s=timeout_s)

    def enabled(self) -> bool:
        return bool(self._enabled and self._endpoint)

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout_s)
        return self._client

    async def capture(self, *, event: str, properties: dict[str, Any]) -> None:
        if not self.enabled():
            return

        payload = {
            "event": str(event),
            "timestamp": _utc_now_iso(),
            "context": {
                "app": self._context.app,
                "version": self._context.version,
                "session_id": self._context.session_id,
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "properties": properties or {},
        }

        try:
            client = await self._ensure_client()
            await client.post(self._endpoint, json=payload)
        except Exception:
            # Never fail tool execution due to telemetry.
            return

    def capture_background(self, *, event: str, properties: dict[str, Any]) -> None:
        if not self.enabled():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (shouldn't happen in FastMCP tools).
            return
        loop.create_task(self.capture(event=event, properties=properties))


@dataclass(frozen=True)
class ToolTiming:
    tool_name: str
    badge: str
    started_at: float


def start_tool_timing(*, tool_name: str, badge: str) -> ToolTiming:
    return ToolTiming(tool_name=tool_name, badge=badge, started_at=time.monotonic())


def finish_tool_timing(timing: ToolTiming) -> int:
    return int(max(0.0, (time.monotonic() - timing.started_at) * 1000.0))

