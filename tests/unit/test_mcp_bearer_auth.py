from __future__ import annotations

import pytest

from lifecycle_mcp.bearer_auth import StaticBearerTokenVerifier


@pytest.mark.asyncio
async def test_static_bearer_token_verifier_accepts_matching_token():
    verifier = StaticBearerTokenVerifier("secret-token-value")
    result = await verifier.verify_token("secret-token-value")
    assert result is not None
    assert result.client_id == "truthexpiry-worker"


@pytest.mark.asyncio
async def test_static_bearer_token_verifier_rejects_mismatch():
    verifier = StaticBearerTokenVerifier("secret-token-value")
    assert await verifier.verify_token("wrong-token") is None
