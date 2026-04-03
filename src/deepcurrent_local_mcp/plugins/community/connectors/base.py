from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol


ExecutionMode = Literal["local", "byok-api", "deepcurrent-gateway"]
Badge = Literal["community", "certified", "official"]


@dataclass(frozen=True)
class ConnectorSpec:
    id: str
    description: str
    input_schema: dict[str, Any]
    execution_mode: ExecutionMode = "local"
    badge: Badge = "community"
    publisher: str = "community"
    docs_url: str | None = None


class Connector(Protocol):
    spec: ConnectorSpec

    async def run(self, *, params: dict[str, Any]) -> dict[str, Any]:
        ...

