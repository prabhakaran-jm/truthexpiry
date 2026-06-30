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
from adapters.llm.mapper import map_extracted_claim_dto
from adapters.llm.prompt import MAX_QUERY_CHARACTERS, build_extraction_prompt
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
            claims = self._interpret_output(output, evidence_map=payload.evidence_map)
        except _KNOWN_FAILURES as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "Claim extraction failure outcome=unavailable duration_ms=%s "
                "evidence_count=%s query_length=%s claim_count=0",
                duration_ms,
                evidence_count,
                query_length,
            )
            raise ClaimExtractionUnavailableError(
                "Claim extraction is temporarily unavailable for this request."
            ) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Claim extraction completed outcome=success duration_ms=%s "
            "evidence_count=%s query_length=%s claim_count=%s",
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
        evidence_map: dict[str, EphemeralRtsHit],
    ) -> list[ExtractedClaim]:
        if output.claim is None:
            return []
        return [map_extracted_claim_dto(output.claim, evidence_map=evidence_map)]
