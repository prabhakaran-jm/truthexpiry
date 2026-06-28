from __future__ import annotations

import logging

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from adapters.lifecycle_mcp.errors import LifecycleMcpResponseError, LifecycleMcpTransportError
from adapters.lifecycle_mcp.mapper import map_structured_content
from lifecycle_mcp.contracts import TOOL_NAME
from truthexpiry.models.claim import ClaimKey
from truthexpiry.models.evidence import LifecycleRecord

logger = logging.getLogger(__name__)


class LifecycleMcpClient:
    def __init__(self, mcp_url: str) -> None:
        self._mcp_url = mcp_url

    async def fetch_records_async(self, key: ClaimKey) -> list[LifecycleRecord]:
        try:
            async with streamable_http_client(self._mcp_url) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    await self._ensure_tool_present(session)
                    result = await session.call_tool(
                        TOOL_NAME,
                        {
                            "entity": key.entity,
                            "attribute": key.attribute,
                            "scope": dict(key.scope.fields),
                        },
                    )
        except LifecycleMcpResponseError:
            raise
        except Exception as exc:  # noqa: BLE001 - map to transport error
            logger.warning(
                "Lifecycle MCP transport failure for tool=%s key=%s",
                TOOL_NAME,
                key.canonical(),
                exc_info=True,
            )
            raise LifecycleMcpTransportError("Lifecycle MCP transport failed") from exc

        try:
            records = map_structured_content(result, key)
        except LifecycleMcpResponseError:
            logger.warning(
                "Lifecycle MCP invalid response for tool=%s key=%s",
                TOOL_NAME,
                key.canonical(),
            )
            raise

        logger.info(
            "Lifecycle MCP fetched records tool=%s key=%s count=%d",
            TOOL_NAME,
            key.canonical(),
            len(records),
        )
        return records

    async def _ensure_tool_present(self, session: ClientSession) -> None:
        tools = await session.list_tools()
        if not any(tool.name == TOOL_NAME for tool in tools.tools):
            raise LifecycleMcpResponseError(
                f"Lifecycle MCP tool missing: {TOOL_NAME!r}"
            )
