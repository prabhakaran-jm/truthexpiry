"""Domain-owned claim extraction schema catalog.

Defines supported entity/attribute pairs and allowed values for live extraction
validation. No provider imports or network behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from truthexpiry.services.claim_key import normalize_token


@dataclass(frozen=True)
class ClaimSchema:
    allowed_stated_values: frozenset[str]
    allowed_scope_keys: frozenset[str]
    required_scope_keys: frozenset[str]
    scope_defaults: Mapping[str, str] = field(default_factory=dict)


def _schema(
    *,
    values: tuple[str, ...],
    scope_keys: tuple[str, ...] = ("plan", "region"),
    required_scope: tuple[str, ...] = ("plan", "region"),
    defaults: Mapping[str, str] | None = None,
) -> ClaimSchema:
    default_map = dict(defaults or {"region": "global"})
    return ClaimSchema(
        allowed_stated_values=frozenset(values),
        allowed_scope_keys=frozenset(scope_keys),
        required_scope_keys=frozenset(required_scope),
        scope_defaults=MappingProxyType(default_map),
    )


_CLAIM_SCHEMA_CATALOG: dict[tuple[str, str], ClaimSchema] = {
    (normalize_token("report_export"), normalize_token("availability")): _schema(
        values=("enabled", "disabled")
    ),
    (normalize_token("analytics_export"), normalize_token("availability")): _schema(
        values=("enabled",)
    ),
    (normalize_token("api_rate_limit"), normalize_token("max_requests")): _schema(
        values=("100", "50")
    ),
    (normalize_token("billing_refund"), normalize_token("policy")): _schema(
        values=("30_days", "60_days")
    ),
    (normalize_token("mobile_push"), normalize_token("delivery")): _schema(
        values=("enabled",)
    ),
    (normalize_token("feature_flag"), normalize_token("rollout")): _schema(
        values=("enabled",)
    ),
    (normalize_token("legacy_api"), normalize_token("sunset")): _schema(
        values=("deprecated",)
    ),
}

CLAIM_SCHEMA_CATALOG: Mapping[tuple[str, str], ClaimSchema] = MappingProxyType(
    _CLAIM_SCHEMA_CATALOG
)


def lookup_claim_schema(entity: str, attribute: str) -> ClaimSchema | None:
    key = (normalize_token(entity), normalize_token(attribute))
    return CLAIM_SCHEMA_CATALOG.get(key)


_STATED_VALUE_ALIASES: dict[str, str] = {
    "available": "enabled",
    "enabled": "enabled",
    "on": "enabled",
    "turned_on": "enabled",
    "switched_on": "enabled",
    "unavailable": "disabled",
    "disabled": "disabled",
    "off": "disabled",
    "turned_off": "disabled",
    "switched_off": "disabled",
    "not_available": "disabled",
    "not_enabled": "disabled",
}


def normalize_stated_value_for_schema(raw_value: str, schema: ClaimSchema) -> str:
    """Map model wording to catalog lifecycle values when unambiguous."""
    token = normalize_token(raw_value)
    if token in schema.allowed_stated_values:
        return token
    alias = _STATED_VALUE_ALIASES.get(token)
    if alias is not None and alias in schema.allowed_stated_values:
        return alias
    if is_numeric_schema(schema):
        digits = "".join(character for character in raw_value if character.isdigit())
        if digits in schema.allowed_stated_values:
            return digits
    return token


def is_numeric_schema(schema: ClaimSchema) -> bool:
    return bool(schema.allowed_stated_values) and all(
        value.isdigit() for value in schema.allowed_stated_values
    )


def is_availability_schema(schema: ClaimSchema) -> bool:
    return schema.allowed_stated_values <= frozenset({"enabled", "disabled"})
