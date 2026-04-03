from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import ConnectorSpec


_MAX_FILE_BYTES_DEFAULT = 20_000_000
_MAX_RESULTS_DEFAULT = 20
_MAX_RECORD_CHARS_DEFAULT = 2_000
_MAX_SNIPPET_CHARS_DEFAULT = 240


def _as_int(value: Any, *, default: int) -> int:
    try:
        n = int(value)
        return n
    except Exception:
        return default


def _as_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return True
        if v in ("0", "false", "no", "n", "off"):
            return False
    return default


def _extract_records(data: Any, *, root_key: str | None) -> tuple[list[Any], str]:
    """
    Return (records, source) where source describes how we found the list.
    """
    if isinstance(data, list):
        return data, "root:list"

    if isinstance(data, dict):
        if root_key and isinstance(data.get(root_key), list):
            return list(data[root_key]), f"root_key:{root_key}"

        for k in ("records", "items", "results", "data"):
            if isinstance(data.get(k), list):
                return list(data[k]), f"auto_key:{k}"

        # Fall back to searching a single object.
        return [data], "root:dict(single)"

    # Primitive (string/number/etc) -> treat as single record.
    return [data], f"root:{type(data).__name__}(single)"


def _json_text(record: Any) -> str:
    if isinstance(record, str):
        return record
    try:
        return json.dumps(record, ensure_ascii=True, sort_keys=True)
    except Exception:
        return str(record)


def _make_snippet(text: str, *, needle: str, case_sensitive: bool, max_chars: int) -> str:
    if not needle:
        return ""
    hay = text if case_sensitive else text.lower()
    ndl = needle if case_sensitive else needle.lower()
    idx = hay.find(ndl)
    if idx < 0:
        return ""

    start = max(0, idx - (max_chars // 2))
    end = min(len(text), idx + len(needle) + (max_chars // 2))
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


@dataclass(frozen=True)
class LocalJsonSearchConnector:
    """
    Simple BYOD connector: search a local JSON file for a substring.

    Intended use:
    - quick lookups in local exported datasets
    - small/medium JSON files (bounded outputs)
    """

    spec: ConnectorSpec = ConnectorSpec(
        id="local_json_search",
        description="Search a local JSON file (list or dict) for substring matches.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to a local JSON file."},
                "query": {"type": "string", "description": "Substring to search for."},
                "root_key": {
                    "type": "string",
                    "description": "Optional key to treat as the record list when JSON is an object.",
                },
                "case_sensitive": {"type": "boolean", "default": False},
                "max_results": {"type": "integer", "default": _MAX_RESULTS_DEFAULT},
                "max_file_bytes": {"type": "integer", "default": _MAX_FILE_BYTES_DEFAULT},
                "max_record_chars": {"type": "integer", "default": _MAX_RECORD_CHARS_DEFAULT},
            },
            "required": ["file_path", "query"],
        },
        execution_mode="local",
        badge="certified",
        publisher="DeepCurrent",
        docs_url=None,
    )

    async def run(self, *, params: dict[str, Any]) -> dict[str, Any]:
        file_path = str((params or {}).get("file_path") or "").strip()
        query = str((params or {}).get("query") or "")
        root_key = (str((params or {}).get("root_key") or "").strip() or None)

        case_sensitive = _as_bool((params or {}).get("case_sensitive"), default=False)
        max_results = max(1, min(_as_int((params or {}).get("max_results"), default=_MAX_RESULTS_DEFAULT), 100))
        max_file_bytes = max(1, _as_int((params or {}).get("max_file_bytes"), default=_MAX_FILE_BYTES_DEFAULT))
        max_record_chars = max(256, _as_int((params or {}).get("max_record_chars"), default=_MAX_RECORD_CHARS_DEFAULT))

        if not file_path:
            return {"ok": False, "error": {"code": "missing_file_path", "message": "Missing file_path"}}
        if not query.strip():
            return {"ok": False, "error": {"code": "missing_query", "message": "Missing query"}}

        path = Path(file_path).expanduser()
        if not path.exists():
            return {"ok": False, "error": {"code": "file_not_found", "message": f"File not found: {path}"}}
        if not path.is_file():
            return {"ok": False, "error": {"code": "not_a_file", "message": f"Not a file: {path}"}}

        try:
            size = path.stat().st_size
        except Exception:
            size = None

        if isinstance(size, int) and size > max_file_bytes:
            return {
                "ok": False,
                "error": {
                    "code": "file_too_large",
                    "message": f"File too large ({size} bytes). Increase max_file_bytes to proceed.",
                },
            }

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except UnicodeDecodeError:
            return {
                "ok": False,
                "error": {"code": "decode_error", "message": "Failed to decode file as UTF-8."},
            }
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "error": {"code": "invalid_json", "message": f"Invalid JSON: {exc.msg}"},
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": {"code": "read_failed", "message": f"Failed reading file: {type(exc).__name__}"},
            }

        records, record_source = _extract_records(data, root_key=root_key)

        matches: list[dict[str, Any]] = []
        scanned = 0
        for idx, record in enumerate(records):
            scanned += 1
            text = _json_text(record)
            hay = text if case_sensitive else text.lower()
            ndl = query if case_sensitive else query.lower()
            if ndl not in hay:
                continue

            snippet = _make_snippet(
                text,
                needle=query,
                case_sensitive=case_sensitive,
                max_chars=_MAX_SNIPPET_CHARS_DEFAULT,
            )
            entry: dict[str, Any] = {"index": idx, "snippet": snippet}

            # Only include a full record when it is reasonably small.
            if len(text) <= max_record_chars:
                entry["record"] = record
            else:
                entry["record_preview"] = text[:max_record_chars] + "...(truncated)"
                entry["record_truncated_to_chars"] = max_record_chars

            matches.append(entry)
            if len(matches) >= max_results:
                break

        return {
            "ok": True,
            "connector_id": self.spec.id,
            "file_path": str(path),
            "file_size_bytes": size,
            "record_source": record_source,
            "query": query,
            "case_sensitive": case_sensitive,
            "scanned_records": scanned,
            "matches_returned": len(matches),
            "matches_limit": max_results,
            "matches_truncated": len(matches) >= max_results,
            "matches": matches,
        }

