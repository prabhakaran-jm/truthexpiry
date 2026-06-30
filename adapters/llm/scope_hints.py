from __future__ import annotations

from adapters.llm.contracts import ExtractedClaimDto
from truthexpiry.services.claim_key import normalize_token


def apply_scope_hints_from_query(
    query: str, claim: ExtractedClaimDto
) -> ExtractedClaimDto:
    """Fill missing scope keys from explicit query wording only."""
    scope = dict(claim.scope)
    normalized_keys = {normalize_token(key) for key in scope}
    lowered = query.lower()

    if "plan" not in normalized_keys:
        if "starter" in lowered:
            scope["plan"] = "starter"
        elif "enterprise" in lowered:
            scope["plan"] = "enterprise"

    if "region" not in normalized_keys and "global" not in normalized_keys:
        scope["region"] = "global"

    if scope == claim.scope:
        return claim
    return claim.model_copy(update={"scope": scope})
