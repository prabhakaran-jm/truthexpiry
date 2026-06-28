from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from adapters.fakes.synthetic_data import REPORT_EXPORT_KEY
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
from adapters.lifecycle_mcp.mapper import map_structured_content
from lifecycle_mcp.contracts import TOOL_NAME
from truthexpiry.models.evidence import LifecycleState

_READINESS_TIMEOUT_SECONDS = 15.0
_SHUTDOWN_TIMEOUT_SECONDS = 5.0


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_is_rebindable(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))
        return True


async def _wait_for_server(url: str) -> None:
    deadline = time.monotonic() + _READINESS_TIMEOUT_SECONDS
    backoff = 0.05
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            async with streamable_http_client(url) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    if any(tool.name == TOOL_NAME for tool in tools.tools):
                        return
        except Exception as exc:  # noqa: BLE001 - readiness polling
            last_error = exc
        await asyncio.sleep(backoff)
        backoff = min(backoff * 1.5, 1.0)
    raise TimeoutError(
        f"Lifecycle MCP server did not become ready at {url}"
    ) from last_error


@pytest.mark.integration
def test_lifecycle_mcp_transport_subprocess_round_trip():
    port = _reserve_local_port()
    url = f"http://127.0.0.1:{port}/mcp"
    env = {
        **os.environ,
        "TRUTH_EXPIRY_LIFECYCLE_MCP_HOST": "127.0.0.1",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_PORT": str(port),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "lifecycle_mcp.server"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        asyncio.run(_wait_for_server(url))

        async def _call_tool_and_validate() -> None:
            async with streamable_http_client(url) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert any(tool.name == TOOL_NAME for tool in tools.tools)
                    result = await session.call_tool(
                        TOOL_NAME,
                        {
                            "entity": REPORT_EXPORT_KEY.entity,
                            "attribute": REPORT_EXPORT_KEY.attribute,
                            "scope": dict(REPORT_EXPORT_KEY.scope.fields),
                        },
                    )
                    records = map_structured_content(result, REPORT_EXPORT_KEY)
                    prod_482 = next(
                        record for record in records if record.record_id == "PROD-482"
                    )
                    assert prod_482.state is LifecycleState.SHIPPED
                    assert prod_482.value == "disabled"

        asyncio.run(_call_tool_and_validate())

        adapter = LifecycleMcpAdapter(url)
        domain_records = adapter.fetch_records(REPORT_EXPORT_KEY)
        assert any(record.record_id == "PROD-482" for record in domain_records)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
        assert proc.poll() is not None
        assert _port_is_rebindable(port)
