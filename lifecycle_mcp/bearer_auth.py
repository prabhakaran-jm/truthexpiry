from __future__ import annotations

import secrets

from mcp.server.auth.provider import AccessToken, TokenVerifier


class StaticBearerTokenVerifier:
    """Validate a single shared bearer token for service-to-service MCP access."""

    def __init__(self, expected_token: str) -> None:
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self._expected_token):
            return None
        return AccessToken(
            token=token,
            client_id="truthexpiry-worker",
            scopes=[],
        )


def build_token_verifier(
    *,
    auth_disabled: bool,
    auth_token: str | None,
) -> TokenVerifier | None:
    if auth_disabled:
        return None
    if auth_token is None:
        return None
    return StaticBearerTokenVerifier(auth_token)
