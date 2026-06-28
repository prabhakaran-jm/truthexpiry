from mcp.server.fastmcp import FastMCP

from lifecycle_mcp.contracts import GetLifecycleEvidenceOutput
from lifecycle_mcp.repository import default_repository
from lifecycle_mcp.server_settings import LifecycleMcpServerSettings


def create_mcp(settings: LifecycleMcpServerSettings | None = None) -> FastMCP:
    resolved = settings or LifecycleMcpServerSettings.from_env()
    repository = default_repository()
    mcp = FastMCP(
        "TruthExpiry Lifecycle Evidence",
        host=resolved.host,
        port=resolved.port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )

    @mcp.tool()
    def get_lifecycle_evidence(
        entity: str,
        attribute: str,
        scope: dict[str, str],
    ) -> GetLifecycleEvidenceOutput:
        records = repository.find_dtos(entity, attribute, scope)
        return GetLifecycleEvidenceOutput(records=records)

    return mcp


def main() -> None:
    settings = LifecycleMcpServerSettings.from_env()
    mcp = create_mcp(settings)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
