from __future__ import annotations

import pytest

from deepcurrent_local_mcp.main import _validated_http_host


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_local_http_accepts_loopback_hosts(host: str) -> None:
    assert _validated_http_host(host) == host


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.5", "example.com"])
def test_local_http_rejects_non_loopback_hosts(host: str) -> None:
    with pytest.raises(ValueError, match="loopback"):
        _validated_http_host(host)
