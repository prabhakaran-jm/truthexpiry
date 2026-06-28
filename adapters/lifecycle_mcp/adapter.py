from adapters.lifecycle_mcp.client import LifecycleMcpClient
from adapters.lifecycle_mcp.errors import LifecycleMcpResponseError, LifecycleMcpTransportError
from adapters.lifecycle_mcp.sync_bridge import run_mcp_call
from truthexpiry.models.claim import ClaimKey
from truthexpiry.models.evidence import LifecycleRecord
from truthexpiry.ports.lifecycle import LifecycleEvidenceUnavailableError


class LifecycleMcpAdapter:
    """Production lifecycle evidence adapter backed by Streamable HTTP MCP."""

    def __init__(self, mcp_url: str, client: LifecycleMcpClient | None = None) -> None:
        self._client = client or LifecycleMcpClient(mcp_url)

    def fetch_records(self, key: ClaimKey) -> list[LifecycleRecord]:
        try:
            return run_mcp_call(lambda: self._client.fetch_records_async(key))
        except (LifecycleMcpTransportError, LifecycleMcpResponseError) as exc:
            raise LifecycleEvidenceUnavailableError(
                "Authoritative lifecycle evidence is currently unavailable."
            ) from exc
