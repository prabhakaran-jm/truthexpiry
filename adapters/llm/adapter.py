from __future__ import annotations

import logging
import time

from pydantic import ValidationError

from adapters.llm.contracts import ClaimExtractionOutputDto
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
from adapters.llm.failure_categories import extraction_failure_category
from adapters.llm.mapper import map_extracted_claim_dto
from adapters.llm.prompt import MAX_QUERY_CHARACTERS, build_extraction_prompt
from adapters.llm.query_hints import (
    apply_query_hints,
    build_query_grounded_claim_dto,
    is_claim_stated_value_grounded_in_query,
)
from adapters.llm.runner import ExtractionAgentRunner, PydanticAiExtractionRunner
from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.ports.llm import ClaimExtractionUnavailableError
from truthexpiry.ports.rts import EphemeralRtsHit, EphemeralRtsHits

logger = logging.getLogger(__name__)

_KNOWN_FAILURES = (
    QueryTooLongError,
    ProviderTimeoutError,
    ProviderTransportError,
    MalformedStructuredOutputError,
    UnknownEvidenceIdError,
    DuplicateEvidenceIdError,
    EmptyEvidenceIdsError,
    UnsupportedClaimSchemaError,
    InvalidScopeError,
    ScopeKeyCollisionError,
    InvalidStatedValueError,
    ValidationError,
)


class PydanticAiClaimExtractionAdapter:
    """Live OpenAI-backed claim extraction adapter."""

    def __init__(self, runner: ExtractionAgentRunner | None = None) -> None:
        self._runner = runner or PydanticAiExtractionRunner()

    def extract_claims(
        self, query: str, hits: EphemeralRtsHits
    ) -> list[ExtractedClaim]:
        started = time.perf_counter()
        query_length = len(query)
        if query_length > MAX_QUERY_CHARACTERS:
            raise ClaimExtractionUnavailableError(
                "Claim extraction is temporarily unavailable for this request."
            ) from QueryTooLongError("Query exceeds maximum length")

        payload = build_extraction_prompt(query, hits)
        evidence_count = len(payload.evidence_map)
        try:
            output = self._runner.run(
                system_prompt="",
                user_prompt=payload.user_prompt,
            )
            claims = self._interpret_output(
                output,
                query=query,
                evidence_map=payload.evidence_map,
                evidence_count=evidence_count,
                query_length=query_length,
                started=started,
            )
        except _KNOWN_FAILURES as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            category = extraction_failure_category(exc)
            logger.warning(
                "Claim extraction failure method=extract_claims outcome=unavailable "
                "category=%s duration_ms=%s evidence_count=%s query_length=%s "
                "claim_count=0",
                category,
                duration_ms,
                evidence_count,
                query_length,
            )
            raise ClaimExtractionUnavailableError(
                "Claim extraction is temporarily unavailable for this request."
            ) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Claim extraction completed method=extract_claims outcome=success "
            "duration_ms=%s evidence_count=%s query_length=%s claim_count=%s",
            duration_ms,
            evidence_count,
            query_length,
            len(claims),
        )
        return claims

    def _interpret_output(
        self,
        output: ClaimExtractionOutputDto,
        *,
        query: str,
        evidence_map: dict[str, EphemeralRtsHit],
        evidence_count: int,
        query_length: int,
        started: float,
    ) -> list[ExtractedClaim]:
        if output.claim is None:
            claim = build_query_grounded_claim_dto(query, evidence_map)
            if claim is None:
                return []
            return [map_extracted_claim_dto(claim, evidence_map=evidence_map)]
        claim = apply_query_hints(query, output.claim)
        if not is_claim_stated_value_grounded_in_query(query, claim):
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "Claim extraction rejected method=extract_claims "
                "outcome=query_value_not_grounded duration_ms=%s evidence_count=%s "
                "query_length=%s claim_count=0",
                duration_ms,
                evidence_count,
                query_length,
            )
            return []
        return [map_extracted_claim_dto(claim, evidence_map=evidence_map)]
