from __future__ import annotations

from adapters.llm.contracts import ExtractedClaimDto
from adapters.llm.mapper import _canonicalize_entity_attribute
from adapters.llm.scope_hints import apply_scope_hints_from_query
from truthexpiry.services.claim_schema import (
    lookup_claim_schema,
    normalize_stated_value_for_schema,
)
from truthexpiry.services.query_grounding import is_stated_value_grounded_in_query


def apply_query_hints(query: str, claim: ExtractedClaimDto) -> ExtractedClaimDto:
    """Apply scope and entity/attribute hints that do not supply stated_value."""
    claim = _apply_entity_attribute_hints_from_query(query, claim)
    return apply_scope_hints_from_query(query, claim)


def is_claim_stated_value_grounded_in_query(
    query: str, claim: ExtractedClaimDto
) -> bool:
    entity, attribute = _canonicalize_entity_attribute(claim.entity, claim.attribute)
    schema = lookup_claim_schema(entity, attribute)
    if schema is None:
        return True
    canonical = normalize_stated_value_for_schema(claim.stated_value, schema)
    if canonical not in schema.allowed_stated_values:
        return True
    return is_stated_value_grounded_in_query(
        query,
        entity=entity,
        attribute=attribute,
        canonical_stated_value=canonical,
        schema=schema,
    )


def _apply_entity_attribute_hints_from_query(
    query: str, claim: ExtractedClaimDto
) -> ExtractedClaimDto:
    lowered = query.lower()
    updates: dict[str, str] = {}
    if "report export" in lowered:
        updates["entity"] = "report_export"
        updates["attribute"] = "availability"
    if "rate limit" in lowered or "rate-limit" in lowered:
        updates["entity"] = "api_rate_limit"
        updates["attribute"] = "max_requests"
    if not updates:
        return claim
    return claim.model_copy(update=updates)
