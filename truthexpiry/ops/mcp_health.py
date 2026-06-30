from __future__ import annotations

import json
from urllib.parse import urlparse


def lifecycle_mcp_health_readyz_url(
    mcp_url: str,
    *,
    health_url: str | None = None,
    health_port: int = 8001,
) -> str:
    """Build the lifecycle MCP ``/readyz`` URL for worker startup polling."""
    if health_url is not None:
        base = health_url.rstrip("/")
        return base if base.endswith("/readyz") else f"{base}/readyz"

    parsed = urlparse(mcp_url)
    host = parsed.hostname
    if not host:
        raise ValueError(f"Invalid lifecycle MCP URL: {mcp_url!r}")
    scheme = parsed.scheme or "http"
    return f"{scheme}://{host}:{health_port}/readyz"


def probe_mcp_health_readyz(*, health_readyz_url: str, timeout_seconds: float) -> bool:
    """Return True when MCP health ``/readyz`` responds with HTTP 200 and status ok."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(  # noqa: S310
        health_readyz_url,
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            if response.status != 200:
                return False
            body = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ):
        return False
    except OSError:
        return False
    return bool(body.get("status") == "ok")
