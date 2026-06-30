from __future__ import annotations

from unittest.mock import MagicMock, patch

from lifecycle_mcp.http_server import run_streamable_http_server
from lifecycle_mcp.server_settings import LifecycleMcpServerSettings


def test_run_streamable_http_server_passes_shutdown_timeout():
    settings = LifecycleMcpServerSettings.from_env(
        {
            "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "1",
            "TRUTH_EXPIRY_MCP_SHUTDOWN_SECONDS": "12.5",
        }
    )
    mcp = MagicMock()
    captured: dict[str, object] = {}

    class _FakeServer:
        def __init__(self, config: object) -> None:
            captured["config"] = config

        async def serve(self) -> None:
            return None

    with (
        patch("lifecycle_mcp.http_server.uvicorn.Config") as config_cls,
        patch("lifecycle_mcp.http_server.uvicorn.Server", _FakeServer),
        patch("lifecycle_mcp.http_server.anyio.run") as anyio_run,
    ):
        config_cls.return_value = MagicMock()

        def _run(coro_factory: object) -> None:
            import asyncio

            coro = coro_factory()  # type: ignore[operator]
            asyncio.run(coro)

        anyio_run.side_effect = _run
        run_streamable_http_server(mcp, settings)

    config_cls.assert_called_once()
    _, kwargs = config_cls.call_args
    assert kwargs["timeout_graceful_shutdown"] == 12
