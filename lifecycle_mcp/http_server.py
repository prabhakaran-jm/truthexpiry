from __future__ import annotations

import anyio
import uvicorn
from mcp.server.fastmcp import FastMCP

from lifecycle_mcp.server_settings import LifecycleMcpServerSettings


def run_streamable_http_server(
    mcp: FastMCP,
    settings: LifecycleMcpServerSettings,
) -> None:
    """Run FastMCP streamable HTTP with uvicorn graceful shutdown timeout."""

    async def _serve() -> None:
        config = uvicorn.Config(
            mcp.streamable_http_app(),
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            timeout_graceful_shutdown=int(settings.shutdown_seconds),
        )
        server = uvicorn.Server(config)
        await server.serve()

    anyio.run(_serve)
