from __future__ import annotations

import httpx
from mcp.shared._httpx_utils import create_mcp_http_client


def build_mcp_http_client(
    *,
    auth_token: str | None,
    timeout_seconds: float,
) -> httpx.AsyncClient:
    headers: dict[str, str] = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    timeout = httpx.Timeout(timeout_seconds)
    if headers:
        return create_mcp_http_client(headers=headers, timeout=timeout)
    return create_mcp_http_client(timeout=timeout)
