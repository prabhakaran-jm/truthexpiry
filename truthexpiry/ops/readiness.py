from __future__ import annotations

import time

from truthexpiry.ops.mcp_health import probe_mcp_health_readyz


def wait_for_mcp_readiness(
    *,
    health_readyz_url: str,
    timeout_seconds: float,
    client_timeout_seconds: float,
    poll_interval_seconds: float = 0.5,
) -> bool:
    """Bounded blocking poll until lifecycle MCP ``/readyz`` returns ready."""
    deadline = time.monotonic() + timeout_seconds
    backoff = poll_interval_seconds
    while time.monotonic() < deadline:
        if probe_mcp_health_readyz(
            health_readyz_url=health_readyz_url,
            timeout_seconds=client_timeout_seconds,
        ):
            return True
        time.sleep(backoff)
        backoff = min(backoff * 1.5, 2.0)
    return False
