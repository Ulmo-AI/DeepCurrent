from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .cloud import CloudAPIError

MAX_RECORDS_PER_CALL = 25
MAX_OUTPUT_FIELDS = 25
MAX_NESTING_DEPTH = 5
MAX_STRING_LENGTH = 50_000
MAX_MAPPING_KEYS = 50

_RECORD_COUNT_KEYS = {
    "additional",
    "context_limit",
    "count",
    "investor_limit",
    "limit",
    "max_contacts",
    "network_limit",
    "people_limit",
    "portfolio_limit",
}
_FIELD_LIST_KEYS = {"contact_fields", "output_fields", "required_fields"}


def _reject(message: str) -> None:
    raise CloudAPIError(
        status_code=400,
        message=message,
        body={"detail": {"code": "mcp_request_limit_exceeded", "message": message}},
    )


def require_bounded_payload(payload: Any) -> None:
    """Reject local-MCP requests that exceed the hosted data-tool contract."""

    def visit(value: Any, *, key: str | None, depth: int) -> None:
        if depth > MAX_NESTING_DEPTH:
            _reject(f"Request nesting exceeds the maximum depth of {MAX_NESTING_DEPTH}.")

        if isinstance(value, str):
            if len(value) > MAX_STRING_LENGTH:
                _reject(f"Request text exceeds {MAX_STRING_LENGTH:,} characters.")
            if key == "input_text":
                records = [line for line in value.splitlines() if line.strip()]
                if len(records) > MAX_RECORDS_PER_CALL:
                    _reject(f"MCP data tools accept at most {MAX_RECORDS_PER_CALL} records per call.")
            return

        if isinstance(value, bool) or value is None:
            return

        if isinstance(value, (int, float)):
            if key in _RECORD_COUNT_KEYS and value > MAX_RECORDS_PER_CALL:
                _reject(f"MCP data tools accept at most {MAX_RECORDS_PER_CALL} records per call.")
            return

        if isinstance(value, Mapping):
            if len(value) > MAX_MAPPING_KEYS:
                _reject(f"Request objects accept at most {MAX_MAPPING_KEYS} fields.")
            for child_key, child_value in value.items():
                if (
                    str(child_key) == "mode"
                    and isinstance(child_value, str)
                    and child_value.strip().lower() == "all"
                ):
                    _reject("MCP selections must name or count at most 25 records.")
                visit(child_value, key=str(child_key), depth=depth + 1)
            return

        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            maximum = MAX_OUTPUT_FIELDS if key in _FIELD_LIST_KEYS else MAX_RECORDS_PER_CALL
            noun = "fields" if key in _FIELD_LIST_KEYS else "records"
            if len(value) > maximum:
                _reject(f"MCP data tools accept at most {maximum} {noun} per call.")
            for child in value:
                visit(child, key=None, depth=depth + 1)

    visit(payload, key=None, depth=0)


def bound_output(value: Any, *, depth: int = 0) -> Any:
    """Recursively cap cloud results before returning them through local MCP."""

    if depth > MAX_NESTING_DEPTH:
        return "[truncated: nesting limit]"
    if isinstance(value, str):
        return (
            value
            if len(value) <= MAX_STRING_LENGTH
            else f"{value[:MAX_STRING_LENGTH]}\n[truncated]"
        )
    if isinstance(value, Mapping):
        return {
            str(key): bound_output(child, depth=depth + 1)
            for key, child in list(value.items())[:MAX_MAPPING_KEYS]
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            bound_output(child, depth=depth + 1)
            for child in value[:MAX_RECORDS_PER_CALL]
        ]
    return value
