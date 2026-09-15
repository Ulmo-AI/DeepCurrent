from deepcurrent_local_mcp.runtime import error_result


def test_error_result_exposes_structured_quota_metadata() -> None:
    result = error_result(
        status_code=429,
        message="Allowance reached.",
        body={
            "detail": {
                "code": "distinct_record_limit_reached",
                "retry_after_seconds": 30,
                "resets_at": "2026-10-01T00:00:00Z",
            }
        },
    )

    assert result["error"]["code"] == "distinct_record_limit_reached"
    assert result["error"]["retry_after_seconds"] == 30
    assert result["error"]["resets_at"] == "2026-10-01T00:00:00Z"


def test_error_result_exposes_transport_request_metadata() -> None:
    result = error_result(
        status_code=429,
        message="Rate limited.",
        body={
            "detail": {"message": "Rate limited."},
            "_transport": {"retry_after_seconds": 17, "request_id": "req-17"},
        },
    )

    assert result["error"]["retry_after_seconds"] == 17
    assert result["error"]["request_id"] == "req-17"
