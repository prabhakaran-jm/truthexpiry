import pytest

from adapters.fakes.synthetic_data import REPORT_EXPORT_KEY
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
from adapters.lifecycle_mcp.client import LifecycleMcpClient
from adapters.lifecycle_mcp.errors import (
    LifecycleMcpResponseError,
    LifecycleMcpTransportError,
)
from truthexpiry.models.evidence import LifecycleRecord
from truthexpiry.ports.lifecycle import LifecycleEvidenceUnavailableError


class _StubClient(LifecycleMcpClient):
    def __init__(self, behavior: str) -> None:
        super().__init__("http://127.0.0.1:0/mcp")
        self._behavior = behavior

    async def fetch_records_async(self, key) -> list[LifecycleRecord]:
        if self._behavior == "transport":
            raise LifecycleMcpTransportError("Lifecycle MCP transport failed")
        if self._behavior == "response":
            raise LifecycleMcpResponseError(
                "MCP tool response missing structuredContent"
            )
        return []


def test_adapter_maps_transport_exception_to_unavailable_error():
    adapter = LifecycleMcpAdapter(
        "http://127.0.0.1:0/mcp", client=_StubClient("transport")
    )
    with pytest.raises(
        LifecycleEvidenceUnavailableError, match="currently unavailable"
    ):
        adapter.fetch_records(REPORT_EXPORT_KEY)


def test_adapter_maps_response_exception_to_unavailable_error():
    adapter = LifecycleMcpAdapter(
        "http://127.0.0.1:0/mcp", client=_StubClient("response")
    )
    with pytest.raises(
        LifecycleEvidenceUnavailableError, match="currently unavailable"
    ):
        adapter.fetch_records(REPORT_EXPORT_KEY)


def test_adapter_does_not_swallow_successful_empty_list():
    adapter = LifecycleMcpAdapter("http://127.0.0.1:0/mcp", client=_StubClient("empty"))
    assert adapter.fetch_records(REPORT_EXPORT_KEY) == []
