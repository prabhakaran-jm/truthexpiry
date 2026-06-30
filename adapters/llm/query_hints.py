from __future__ import annotations

from adapters.llm.contracts import ExtractedClaimDto
from adapters.llm.mapper import _canonicalize_entity_attribute
from adapters.llm.scope_hints import apply_scope_hints_from_query
from truthexpiry.ports.rts import EphemeralRtsHit
from truthexpiry.services.claim_schema import (
    lookup_claim_schema,
    normalize_stated_value_for_schema,
)
from truthexpiry.services.query_grounding import (
    ground_availability_polarity,
    ground_numeric_values,
    is_stated_value_grounded_in_query,
)


def apply_query_hints(query: str, claim: ExtractedClaimDto) -> ExtractedClaimDto:
    """Apply scope and entity/attribute hints that do not supply stated_value."""
    claim = _apply_entity_attribute_hints_from_query(query, claim)
    return apply_scope_hints_from_query(query, claim)


def build_query_grounded_claim_dto(
    query: str,
    evidence_map: dict[str, EphemeralRtsHit],
) -> ExtractedClaimDto | None:
    """Build a claim from query-grounded values when the model returns null."""
    if not evidence_map:
        return None
    evidence_ids = [
        min(evidence_map.keys(), key=lambda item: int(item.split("-", 1)[1]))
    ]
    lowered = query.lower()

    if "rate limit" in lowered or "rate-limit" in lowered:
        schema = lookup_claim_schema("api_rate_limit", "max_requests")
        if schema is None:
            return None
        grounded_values = ground_numeric_values(query, schema.allowed_stated_values)
        if len(grounded_values) != 1:
            return None
        claim = ExtractedClaimDto(
            entity="api_rate_limit",
            attribute="max_requests",
            scope={},
            stated_value=next(iter(grounded_values)),
            evidence_ids=evidence_ids,
        )
        return apply_scope_hints_from_query(query, claim)

    if "report export" in lowered:
        stated_value = ground_availability_polarity(query)
        if stated_value is None:
            return None
        claim = ExtractedClaimDto(
            entity="report_export",
            attribute="availability",
            scope={},
            stated_value=stated_value,
            evidence_ids=evidence_ids,
        )
        return apply_scope_hints_from_query(query, claim)

    return None


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
