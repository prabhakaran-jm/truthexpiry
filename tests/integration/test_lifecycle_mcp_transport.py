from __future__ import annotations

import asyncio
import os
import signal
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
_PORT_RELEASE_TIMEOUT_SECONDS = 5.0


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_accepts_connections(host: str, port: int, *, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False
        return True


def _force_kill_process_tree(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _kill_windows_listeners_on_port(port: int) -> None:
    if sys.platform != "win32":
        return
    result = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    port_token = f":{port}"
    killed_any = False
    for line in result.stdout.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address = parts[1]
        if not local_address.endswith(port_token):
            continue
        pid_str = parts[-1]
        if not pid_str.isdigit():
            continue
        subprocess.run(
            ["taskkill", "/PID", pid_str, "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        killed_any = True
    if killed_any:
        return
    # Parent PID may already be gone; fall back to any LISTENING row for the port.
    for line in result.stdout.splitlines():
        if "LISTENING" not in line or port_token not in line:
            continue
        pid_str = line.split()[-1]
        if pid_str.isdigit():
            subprocess.run(
                ["taskkill", "/PID", pid_str, "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def _shutdown_server_subprocess(
    proc: subprocess.Popen[bytes], *, host: str, port: int
) -> None:
    root_pid = proc.pid
    proc.terminate()
    if sys.platform == "win32":
        _force_kill_process_tree(root_pid)
    try:
        proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _force_kill_process_tree(root_pid)
        proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)

    if proc.poll() is None:
        _force_kill_process_tree(root_pid)
        proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)

    if sys.platform == "win32" and _port_accepts_connections(host, port):
        _kill_windows_listeners_on_port(port)

    assert proc.poll() is not None
    _wait_until_port_stops_accepting_connections(host, port)


def _wait_until_port_stops_accepting_connections(
    host: str,
    port: int,
    *,
    timeout_seconds: float = _PORT_RELEASE_TIMEOUT_SECONDS,
) -> None:
    """Poll until nothing accepts TCP connections on host:port.

    Rebinding the port is not reliable on Windows because client sockets may
    remain in TIME_WAIT even after the server process exits. A refused connect
    proves the server is no longer listening.
    """
    deadline = time.monotonic() + timeout_seconds
    backoff = 0.05
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
            except ConnectionRefusedError:
                return
            except (TimeoutError, socket.timeout):
                return
            except OSError as exc:
                # Windows: WSAECONNREFUSED (10061) or WSAETIMEDOUT (10060).
                if exc.errno in {10061, 111, 10060}:
                    return
        time.sleep(backoff)
        backoff = min(backoff * 1.5, 0.5)
    raise AssertionError(
        f"Port {host}:{port} still accepts TCP connections after shutdown"
    )


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
        _shutdown_server_subprocess(proc, host="127.0.0.1", port=port)
