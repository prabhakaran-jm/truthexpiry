from __future__ import annotations

import time


def wait_for_mcp_readiness(
    *,
    mcp_url: str,
    auth_token: str | None,
    timeout_seconds: float,
    client_timeout_seconds: float,
    poll_interval_seconds: float = 0.5,
) -> bool:
    """Bounded blocking poll until lifecycle MCP accepts MCP initialize."""
    from adapters.lifecycle_mcp.client import LifecycleMcpClient
    from adapters.lifecycle_mcp.sync_bridge import run_mcp_call

    client = LifecycleMcpClient(
        mcp_url,
        auth_token=auth_token,
        timeout_seconds=client_timeout_seconds,
    )
    deadline = time.monotonic() + timeout_seconds
    backoff = poll_interval_seconds
    while time.monotonic() < deadline:
        ready = run_mcp_call(client.probe_readiness)
        if ready:
            return True
        time.sleep(backoff)
        backoff = min(backoff * 1.5, 2.0)
    return False
