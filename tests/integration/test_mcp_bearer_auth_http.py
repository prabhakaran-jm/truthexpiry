from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from adapters.lifecycle_mcp.http_client import build_mcp_http_client
from lifecycle_mcp.contracts import TOOL_NAME

_READINESS_TIMEOUT_SECONDS = 15.0


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(*, port: int, health_port: int, token: str) -> subprocess.Popen:
    env = {
        **os.environ,
        "TRUTH_EXPIRY_LIFECYCLE_MCP_HOST": "127.0.0.1",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_PORT": str(port),
        "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT": str(health_port),
        "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": token,
        "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "0",
    }
    return subprocess.Popen(
        [sys.executable, "-m", "lifecycle_mcp.server"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _wait_for_health(health_port: int) -> None:
    deadline = time.monotonic() + _READINESS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:{health_port}/readyz",
                    timeout=1.0,
                )
                if response.status_code == 200:
                    return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.2)
    raise TimeoutError("MCP health endpoint did not become ready")


async def _initialize_with_client(url: str, client: httpx.AsyncClient) -> None:
    async with streamable_http_client(url, http_client=client) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            await session.list_tools()


@pytest.mark.integration
def test_mcp_health_readyz_unauthenticated():
    port = _reserve_local_port()
    health_port = _reserve_local_port()
    token = "test-bearer-token-value"
    proc = _start_server(port=port, health_port=health_port, token=token)
    try:
        asyncio.run(_wait_for_health(health_port))
        response = httpx.get(f"http://127.0.0.1:{health_port}/readyz", timeout=2.0)
        assert response.status_code == 200
        assert token not in response.text
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.integration
def test_mcp_transport_rejects_missing_authorization():
    port = _reserve_local_port()
    health_port = _reserve_local_port()
    token = "expected-auth-token"
    proc = _start_server(port=port, health_port=health_port, token=token)
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        asyncio.run(_wait_for_health(health_port))
        client = build_mcp_http_client(auth_token=None, timeout_seconds=5.0)

        async def _attempt() -> None:
            try:
                await _initialize_with_client(url, client)
            finally:
                await client.aclose()

        with pytest.raises(Exception):
            asyncio.run(_attempt())
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.integration
@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer ",
        "Basic abc",
        "Bearer wrong-token",
    ],
)
def test_mcp_transport_rejects_invalid_authorization(authorization: str):
    port = _reserve_local_port()
    health_port = _reserve_local_port()
    token = "expected-auth-token"
    proc = _start_server(port=port, health_port=health_port, token=token)
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        asyncio.run(_wait_for_health(health_port))
        client = build_mcp_http_client(auth_token=None, timeout_seconds=5.0)
        client.headers["Authorization"] = authorization

        async def _attempt() -> None:
            try:
                await _initialize_with_client(url, client)
            finally:
                await client.aclose()

        with pytest.raises(Exception):
            asyncio.run(_attempt())
        assert token not in authorization or authorization != f"Bearer {token}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.integration
def test_mcp_transport_accepts_correct_bearer_token():
    port = _reserve_local_port()
    health_port = _reserve_local_port()
    token = "expected-auth-token"
    proc = _start_server(port=port, health_port=health_port, token=token)
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        asyncio.run(_wait_for_health(health_port))

        async def _call() -> None:
            client = build_mcp_http_client(auth_token=token, timeout_seconds=5.0)
            try:
                await _initialize_with_client(url, client)
                async with streamable_http_client(url, http_client=client) as (
                    read_stream,
                    write_stream,
                    _,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        tools = await session.list_tools()
                        assert any(tool.name == TOOL_NAME for tool in tools.tools)
            finally:
                await client.aclose()

        asyncio.run(_call())
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_worker_client_builds_authorization_header():
    client = build_mcp_http_client(
        auth_token="header-token-value",
        timeout_seconds=1.0,
    )
    assert client.headers.get("Authorization") == "Bearer header-token-value"
