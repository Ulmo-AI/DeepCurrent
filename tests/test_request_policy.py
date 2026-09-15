from __future__ import annotations

import pytest

from deepcurrent_local_mcp.cloud import CloudAPIError
from deepcurrent_local_mcp.policy import require_bounded_payload


def test_accepts_payload_at_public_mcp_boundary() -> None:
    require_bounded_payload(
        {
            "slots": {"limit": 25, "wallet_addresses": [f"0x{i:040x}" for i in range(25)]},
            "output_fields": [f"field_{i}" for i in range(25)],
        }
    )


@pytest.mark.parametrize(
    "key",
    [
        "limit",
        "count",
        "max_contacts",
        "people_limit",
        "additional",
        "context_limit",
        "network_limit",
        "investor_limit",
        "portfolio_limit",
    ],
)
def test_rejects_numeric_record_bound_above_25(key: str) -> None:
    with pytest.raises(CloudAPIError, match="25 records"):
        require_bounded_payload({key: 26})


def test_rejects_more_than_25_records_or_fields() -> None:
    with pytest.raises(CloudAPIError, match="25 records"):
        require_bounded_payload({"rows": [{"id": i} for i in range(26)]})

    with pytest.raises(CloudAPIError, match="25 fields"):
        require_bounded_payload({"output_fields": [f"field_{i}" for i in range(26)]})


def test_rejects_excessive_nesting_and_pasted_rows() -> None:
    nested: object = "value"
    for _ in range(6):
        nested = {"next": nested}
    with pytest.raises(CloudAPIError, match="nesting"):
        require_bounded_payload({"payload": nested})

    with pytest.raises(CloudAPIError, match="25 records"):
        require_bounded_payload({"input_text": "\n".join(f"company-{i}" for i in range(26))})


def test_rejects_select_all_mode() -> None:
    with pytest.raises(CloudAPIError, match="at most 25 records"):
        require_bounded_payload({"selection": {"mode": "all"}})
