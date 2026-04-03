from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LocalMCPConfig:
    api_url: str
    api_key: str | None


def _normalize_base_url(url: str) -> str:
    url = (url or "").strip()
    return url.rstrip("/")


def _config_paths() -> list[Path]:
    # Keep this simple and cross-platform. Users can always rely on env vars.
    home = Path.home()
    return [
        home / ".config" / "deepcurrent" / "local-mcp.json",
        home / ".deepcurrent" / "local-mcp.json",
    ]


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        # Fail closed: if config is malformed, act as if it's missing.
        return {}


def load_config() -> LocalMCPConfig:
    """
    Config precedence:
    1) Environment variables
    2) Config file (~/.config/deepcurrent/local-mcp.json or ~/.deepcurrent/local-mcp.json)
    3) Defaults
    """
    # Defaults
    api_url = "https://api.deepcurrent.app"
    api_key: str | None = None

    # Config file
    for p in _config_paths():
        data = _read_json_file(p)
        if not data:
            continue
        if isinstance(data.get("api_url"), str) and data["api_url"].strip():
            api_url = data["api_url"].strip()
        if isinstance(data.get("api_key"), str) and data["api_key"].strip():
            api_key = data["api_key"].strip()
        break

    # Environment variables override
    api_url = os.getenv("DEEPCURRENT_API_URL", api_url)
    api_key = os.getenv("DEEPCURRENT_API_KEY", api_key)

    return LocalMCPConfig(
        api_url=_normalize_base_url(api_url),
        api_key=(api_key.strip() if isinstance(api_key, str) and api_key.strip() else None),
    )

