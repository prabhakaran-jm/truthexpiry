"""Deterministic query-value grounding for live claim extraction."""

from __future__ import annotations

import re

from truthexpiry.services.claim_key import normalize_token
from truthexpiry.services.claim_schema import (
    ClaimSchema,
    is_availability_schema,
    is_numeric_schema,
)

_DISABLED_AVAILABILITY_PHRASES: tuple[str, ...] = (
    "not available",
    "not enabled",
    "switched off",
    "turned off",
    "unavailable",
    "disabled",
)

_ENABLED_AVAILABILITY_PHRASES: tuple[str, ...] = (
    "switched on",
    "turned on",
    "enabled",
    "available",
)


def _contains_word_token(text: str, token: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", text) is not None


def _is_informational_proposition_query(normalized: str) -> bool:
    padded = f" {normalized} "
    return normalized.startswith("tell me about") or " tell me about " in padded


def _bare_on_signals_enabled(normalized: str) -> bool:
    if not _contains_word_token(normalized, "on"):
        return False
    if re.search(r"\bon the\b", normalized):
        return False
    if re.search(r"\bon a\b", normalized):
        return False
    return True


def ground_availability_polarity(query: str) -> str | None:
    """Return canonical enabled/disabled when the query states polarity, else None."""
    normalized = query.strip().lower()
    if _is_informational_proposition_query(normalized):
        return None
    for phrase in _DISABLED_AVAILABILITY_PHRASES:
        if phrase in normalized:
            return "disabled"
    if _contains_word_token(normalized, "off"):
        return "disabled"

    for phrase in _ENABLED_AVAILABILITY_PHRASES:
        if phrase in normalized:
            return "enabled"
    if _bare_on_signals_enabled(normalized):
        return "enabled"

    return None


def ground_numeric_values(query: str, allowed_values: frozenset[str]) -> frozenset[str]:
    """Return allowed numeric values explicitly present in the query."""
    grounded: set[str] = set()
    for value in allowed_values:
        if _contains_word_token(query, value):
            grounded.add(value)
    return frozenset(grounded)


def is_stated_value_grounded_in_query(
    query: str,
    *,
    entity: str,
    attribute: str,
    canonical_stated_value: str,
    schema: ClaimSchema,
) -> bool:
    entity = normalize_token(entity)
    attribute = normalize_token(attribute)
    if entity == "report_export" and attribute == "availability":
        grounded = ground_availability_polarity(query)
        return grounded is not None and grounded == canonical_stated_value

    if entity == "api_rate_limit" and attribute == "max_requests":
        grounded_values = ground_numeric_values(query, schema.allowed_stated_values)
        return canonical_stated_value in grounded_values

    if is_availability_schema(schema):
        grounded_polarity = ground_availability_polarity(query)
        return (
            grounded_polarity is not None
            and grounded_polarity == canonical_stated_value
        )

    if is_numeric_schema(schema):
        grounded_values = ground_numeric_values(query, schema.allowed_stated_values)
        return canonical_stated_value in grounded_values

    token = normalize_token(canonical_stated_value)
    return token in normalize_token(query)
