"""Deterministic query-only claim recovery when the provider returns claim=null."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from truthexpiry.services.claim_key import normalize_token
from truthexpiry.services.claim_schema import (
    ClaimSchema,
    lookup_claim_schema,
)
from truthexpiry.services.query_grounding import (
    ground_availability_polarity,
    ground_numeric_values,
)


@dataclass(frozen=True)
class GroundedQueryClaim:
    entity: str
    attribute: str
    scope: MappingProxyType[str, str]
    stated_value: str


def extract_grounded_claim_from_query(query: str) -> GroundedQueryClaim | None:
    """Extract exactly one catalog-supported claim from query text only."""
    entity_attribute = _identify_entity_attribute_from_query(query)
    if entity_attribute is None:
        return None
    entity, attribute = entity_attribute
    schema = lookup_claim_schema(entity, attribute)
    if schema is None:
        return None

    stated_value = _stated_value_from_query(query, entity, attribute, schema)
    if stated_value is None:
        return None

    scope = _scope_from_query(query, schema)
    if scope is None:
        return None

    return GroundedQueryClaim(
        entity=entity,
        attribute=attribute,
        scope=MappingProxyType(scope),
        stated_value=stated_value,
    )


def _identify_entity_attribute_from_query(query: str) -> tuple[str, str] | None:
    lowered = query.lower()
    candidates: list[tuple[str, str]] = []
    if "report export" in lowered:
        candidates.append(("report_export", "availability"))
    if "rate limit" in lowered or "rate-limit" in lowered:
        candidates.append(("api_rate_limit", "max_requests"))
    if len(candidates) != 1:
        return None
    return candidates[0]


def _stated_value_from_query(
    query: str,
    entity: str,
    attribute: str,
    schema: ClaimSchema,
) -> str | None:
    entity = normalize_token(entity)
    attribute = normalize_token(attribute)
    if entity == "report_export" and attribute == "availability":
        return ground_availability_polarity(query)
    if entity == "api_rate_limit" and attribute == "max_requests":
        grounded_values = ground_numeric_values(query, schema.allowed_stated_values)
        if len(grounded_values) != 1:
            return None
        return next(iter(grounded_values))
    return None


def _scope_from_query(query: str, schema: ClaimSchema) -> dict[str, str] | None:
    scope = dict(schema.scope_defaults)
    lowered = query.lower()
    if "plan" not in scope:
        if "starter" in lowered:
            scope["plan"] = "starter"
        elif "enterprise" in lowered:
            scope["plan"] = "enterprise"
    if "region" not in scope:
        scope["region"] = "global"

    missing = schema.required_scope_keys - set(scope)
    if missing:
        return None
    for key in scope:
        if normalize_token(key) not in schema.allowed_scope_keys:
            return None
    return scope
