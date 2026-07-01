"""Deterministic query-only claim recovery when the provider returns claim=null."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from truthexpiry.services.claim_key import normalize_token
from truthexpiry.services.claim_schema import (
    ClaimSchema,
    is_availability_schema,
    is_numeric_schema,
    lookup_claim_schema,
)
from truthexpiry.services.query_grounding import (
    ground_availability_polarity,
    ground_numeric_values,
)
from truthexpiry.services.query_or_decomposition import iter_query_candidates

_ENTITY_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("report_export", "availability", ("report export", "export reports")),
    (
        "api_rate_limit",
        "max_requests",
        ("rate limit", "rate-limit", "api limit", "request limit", "requests per"),
    ),
    ("analytics_export", "availability", ("analytics export",)),
    ("billing_refund", "policy", ("refund policy", "billing refund", "enterprise refund", "refund")),
    ("mobile_push", "delivery", ("mobile push", "push notification", "push delivery")),
    ("feature_flag", "rollout", ("feature flag", "feature rollout", "flag rollout")),
    ("legacy_api", "sunset", ("legacy api", "api sunset", "api deprecation")),
)


@dataclass(frozen=True)
class GroundedQueryClaim:
    entity: str
    attribute: str
    scope: MappingProxyType[str, str]
    stated_value: str


def extract_grounded_claims_from_query(query: str) -> list[GroundedQueryClaim]:
    """Extract one or more catalog-supported claims from query text only."""
    claims: list[GroundedQueryClaim] = []
    seen: set[tuple[str, str, tuple[tuple[str, str], ...], str]] = set()
    for candidate in iter_query_candidates(query):
        claim = _extract_single_grounded_claim(candidate)
        if claim is None:
            continue
        identity = (
            claim.entity,
            claim.attribute,
            tuple(sorted(claim.scope.items())),
            claim.stated_value,
        )
        if identity in seen:
            continue
        seen.add(identity)
        claims.append(claim)
    return claims


def extract_grounded_claim_from_query(query: str) -> GroundedQueryClaim | None:
    """Extract exactly one catalog-supported claim from query text only."""
    claims = extract_grounded_claims_from_query(query)
    if len(claims) == 1:
        return claims[0]
    return None


def _extract_single_grounded_claim(query: str) -> GroundedQueryClaim | None:
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


def _matched_entities(query: str) -> tuple[tuple[str, str], ...]:
    lowered = query.lower()
    matches: list[tuple[str, str]] = []
    for entity, attribute, phrases in _ENTITY_PATTERNS:
        if any(phrase in lowered for phrase in phrases):
            matches.append((entity, attribute))
    if (
        "export" in lowered
        and "analytics export" not in lowered
        and ("report_export", "availability") not in matches
    ):
        matches.append(("report_export", "availability"))
    return tuple(dict.fromkeys(matches))


def detect_catalog_entities_in_query(query: str) -> tuple[tuple[str, str], ...]:
    """Return every catalog entity/attribute pair referenced in the query."""
    return _matched_entities(query)


def _identify_entity_attribute_from_query(query: str) -> tuple[str, str] | None:
    matches = _matched_entities(query)
    if len(matches) != 1:
        return None
    return matches[0]


def _stated_value_from_query(
    query: str,
    entity: str,
    attribute: str,
    schema: ClaimSchema,
) -> str | None:
    entity = normalize_token(entity)
    attribute = normalize_token(attribute)

    if entity == "billing_refund" and attribute == "policy":
        lowered = query.lower()
        if "60" in lowered and "day" in lowered:
            return "60_days"
        if "30" in lowered and "day" in lowered:
            return "30_days"
        return None

    if is_availability_schema(schema):
        return ground_availability_polarity(query)

    if is_numeric_schema(schema):
        grounded_values = ground_numeric_values(query, schema.allowed_stated_values)
        if len(grounded_values) != 1:
            return None
        return next(iter(grounded_values))

    lowered = query.lower()
    for value in schema.allowed_stated_values:
        token = value.replace("_", " ")
        if token in lowered or value in lowered:
            return value
    return None


def _scope_from_query(query: str, schema: ClaimSchema) -> dict[str, str] | None:
    scope = dict(schema.scope_defaults)
    lowered = query.lower()
    if "plan" in schema.required_scope_keys or "plan" in schema.allowed_scope_keys:
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
