from __future__ import annotations

import asyncio

from lifecycle_mcp.bearer_auth import StaticBearerTokenVerifier


def test_static_bearer_token_verifier_accepts_matching_token():
    async def _run() -> None:
        verifier = StaticBearerTokenVerifier("secret-token-value")
        result = await verifier.verify_token("secret-token-value")
        assert result is not None
        assert result.client_id == "truthexpiry-worker"

    asyncio.run(_run())


def test_static_bearer_token_verifier_rejects_mismatch():
    async def _run() -> None:
        verifier = StaticBearerTokenVerifier("secret-token-value")
        assert await verifier.verify_token("wrong-token") is None

    asyncio.run(_run())
