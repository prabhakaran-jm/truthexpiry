from __future__ import annotations

from truthexpiry.models.claim import EvidenceRef, ExtractedClaim
from truthexpiry.ports.rts import EphemeralRtsHit
from truthexpiry.services.claim_key import build_claim_key, normalize_token
from truthexpiry.services.claim_schema import ClaimSchema, lookup_claim_schema
from truthexpiry.services.rts_sanitizer import ephemeral_hit_to_evidence_refs

from adapters.llm.contracts import ExtractedClaimDto
from adapters.llm.errors import (
    DuplicateEvidenceIdError,
    EmptyEvidenceIdsError,
    InvalidScopeError,
    InvalidStatedValueError,
    ScopeKeyCollisionError,
    UnknownEvidenceIdError,
    UnsupportedClaimSchemaError,
)


def _normalize_scope(scope: dict[str, str], schema: ClaimSchema) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_key, raw_value in scope.items():
        key = normalize_token(raw_key)
        if key in normalized:
            raise ScopeKeyCollisionError(
                f"Scope key collision after normalization: {raw_key!r}"
            )
        value = normalize_token(raw_value)
        if key not in schema.allowed_scope_keys:
            raise InvalidScopeError(f"Unknown scope key: {raw_key!r}")
        normalized[key] = value
    return normalized


def _apply_scope_defaults(scope: dict[str, str], schema: ClaimSchema) -> dict[str, str]:
    merged = dict(schema.scope_defaults)
    merged.update(scope)
    return merged


def _validate_required_scope(scope: dict[str, str], schema: ClaimSchema) -> None:
    missing = schema.required_scope_keys - set(scope)
    if missing:
        raise InvalidScopeError(
            f"Missing required scope keys: {', '.join(sorted(missing))}"
        )


def _map_evidence_refs(
    evidence_ids: list[str],
    evidence_map: dict[str, EphemeralRtsHit],
) -> tuple[EvidenceRef, ...]:
    if not evidence_ids:
        raise EmptyEvidenceIdsError("Non-null claim requires evidence_ids")

    seen: set[str] = set()
    ordered_ids: list[str] = []
    for evidence_id in evidence_ids:
        if evidence_id in seen:
            raise DuplicateEvidenceIdError(f"Duplicate evidence ID: {evidence_id!r}")
        seen.add(evidence_id)
        if evidence_id not in evidence_map:
            raise UnknownEvidenceIdError(f"Unknown evidence ID: {evidence_id!r}")
        ordered_ids.append(evidence_id)

    # Preserve deterministic RTS order regardless of model-return order.
    sorted_ids = sorted(ordered_ids, key=lambda item: int(item.split("-", 1)[1]))
    refs: list[EvidenceRef] = []
    for evidence_id in sorted_ids:
        hit = evidence_map[evidence_id]
        refs.extend(ephemeral_hit_to_evidence_refs(hit))

    if not refs:
        raise UnknownEvidenceIdError("Evidence IDs did not resolve to references")
    return tuple(refs)


def map_extracted_claim_dto(
    claim: ExtractedClaimDto,
    *,
    evidence_map: dict[str, EphemeralRtsHit],
) -> ExtractedClaim:
    entity = normalize_token(claim.entity)
    attribute = normalize_token(claim.attribute)
    schema = lookup_claim_schema(entity, attribute)
    if schema is None:
        raise UnsupportedClaimSchemaError(
            f"Unsupported entity/attribute: {entity}|{attribute}"
        )

    stated_value = normalize_token(claim.stated_value)
    if stated_value not in schema.allowed_stated_values:
        raise InvalidStatedValueError(
            f"Invalid stated_value {stated_value!r} for {entity}|{attribute}"
        )

    scope = _normalize_scope(claim.scope, schema)
    scope = _apply_scope_defaults(scope, schema)
    _validate_required_scope(scope, schema)

    evidence_refs = _map_evidence_refs(claim.evidence_ids, evidence_map)
    claim_key = build_claim_key(entity, attribute, scope)
    return ExtractedClaim(
        key=claim_key,
        stated_value=stated_value,
        evidence_refs=evidence_refs,
        required_scope_fields=tuple(sorted(schema.required_scope_keys)),
    )
