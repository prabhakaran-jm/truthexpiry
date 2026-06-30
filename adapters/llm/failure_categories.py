from __future__ import annotations

from pydantic import ValidationError

from adapters.llm.errors import (
    DuplicateEvidenceIdError,
    EmptyEvidenceIdsError,
    InvalidScopeError,
    InvalidStatedValueError,
    MalformedStructuredOutputError,
    ProviderTimeoutError,
    ProviderTransportError,
    QueryTooLongError,
    ScopeKeyCollisionError,
    UnknownEvidenceIdError,
    UnsupportedClaimSchemaError,
)


def extraction_failure_category(exc: Exception) -> str:
    if isinstance(exc, ProviderTimeoutError):
        return "provider_timeout"
    if isinstance(exc, ProviderTransportError):
        return "provider_transport"
    if isinstance(exc, MalformedStructuredOutputError):
        return "structured_output_invalid"
    if isinstance(exc, ValidationError):
        return "structured_output_invalid"
    if isinstance(exc, UnsupportedClaimSchemaError):
        return "unsupported_claim_schema"
    if isinstance(exc, InvalidStatedValueError):
        return "invalid_stated_value"
    if isinstance(exc, (InvalidScopeError, ScopeKeyCollisionError)):
        return "invalid_scope"
    if isinstance(exc, EmptyEvidenceIdsError):
        return "missing_evidence_ids"
    if isinstance(exc, DuplicateEvidenceIdError):
        return "duplicate_evidence_id"
    if isinstance(exc, UnknownEvidenceIdError):
        message = str(exc)
        if "did not resolve" in message:
            return "evidence_ref_unresolvable"
        return "unknown_evidence_id"
    if isinstance(exc, QueryTooLongError):
        return "query_too_long"
    return "structured_output_invalid"
