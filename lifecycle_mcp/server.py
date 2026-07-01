import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from lifecycle_mcp.bearer_auth import build_token_verifier
from lifecycle_mcp.contracts import GetLifecycleEvidenceOutput
from lifecycle_mcp.repository import LifecycleRecordRepository, default_repository
from lifecycle_mcp.server_settings import LifecycleMcpServerSettings
from lifecycle_mcp.http_server import run_streamable_http_server
from lifecycle_mcp.structural_check import parse_cli_args, run_structural_check
from truthexpiry.config import ConfigError
from truthexpiry.ops.health import McpReadinessState, start_mcp_health_server

_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_REPO_ROOT / ".env", override=False)


def create_mcp(
    settings: LifecycleMcpServerSettings | None = None,
    *,
    repository: LifecycleRecordRepository | None = None,
) -> FastMCP:
    resolved = settings or LifecycleMcpServerSettings.from_env()
    if repository is None:
        if resolved.dataset_path is not None:
            repository = LifecycleRecordRepository(Path(resolved.dataset_path))
        else:
            repository = default_repository()

    token_verifier = None
    auth_settings = None
    if not resolved.auth_disabled:
        token = resolved.auth_token.get_secret() if resolved.auth_token else None
        token_verifier = build_token_verifier(
            auth_disabled=False,
            auth_token=token,
        )
        if token_verifier is not None:
            resource_url = f"http://{resolved.host}:{resolved.port}/mcp"
            auth_settings = AuthSettings(
                issuer_url=AnyHttpUrl("https://truthexpiry.internal/auth"),
                resource_server_url=AnyHttpUrl(resource_url),
            )

    mcp = FastMCP(
        "TruthExpiry Lifecycle Evidence",
        host=resolved.host,
        port=resolved.port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        token_verifier=token_verifier,
        auth=auth_settings,
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
    if parse_cli_args():
        raise SystemExit(run_structural_check())

    settings = LifecycleMcpServerSettings.from_env()
    try:
        settings.validate_runtime()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    readiness = McpReadinessState()
    readiness.set_configuration("ok")

    try:
        if settings.dataset_path is not None:
            LifecycleRecordRepository(Path(settings.dataset_path))
        else:
            default_repository()
        readiness.set_dataset("ok")
    except Exception:
        readiness.set_dataset("unavailable")
        print("Lifecycle dataset failed to load", file=sys.stderr)
        raise SystemExit(1) from None

    health_server = start_mcp_health_server(
        settings.host,
        settings.health_port,
        readiness,
    )

    try:
        mcp = create_mcp(settings)
        readiness.set_tool_registration("ok")
    except Exception:
        readiness.set_tool_registration("unavailable")
        health_server.stop()
        print("Lifecycle MCP tool registration failed", file=sys.stderr)
        raise SystemExit(1) from None

    try:
        run_streamable_http_server(mcp, settings)
    finally:
        health_server.stop()


if __name__ == "__main__":
    main()
