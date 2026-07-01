from __future__ import annotations

import json
from urllib.parse import urlparse, urlunparse

from truthexpiry.config.common import ConfigError


def _format_netloc(hostname: str, port: int) -> str:
    if ":" in hostname and not hostname.startswith("["):
        return f"[{hostname}]:{port}"
    return f"{hostname}:{port}"


def lifecycle_mcp_health_readyz_url(
    mcp_url: str,
    *,
    health_url: str | None = None,
    health_port: int = 8001,
) -> str:
    """Build the lifecycle MCP ``/readyz`` URL for worker readiness polling."""
    if health_url is not None:
        base = health_url.strip().rstrip("/")
        if not base:
            raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_URL is required")
        return base if base.endswith("/readyz") else f"{base}/readyz"

    parsed = urlparse(mcp_url.strip())
    scheme = parsed.scheme.lower() if parsed.scheme else ""
    if scheme not in {"http", "https"}:
        raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_URL must use http or https")

    hostname = parsed.hostname
    if not hostname:
        raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_URL is invalid")

    netloc = _format_netloc(hostname, health_port)
    return urlunparse((scheme, netloc, "/readyz", "", "", ""))


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
