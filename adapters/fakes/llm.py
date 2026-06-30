import re

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.ports.rts import EphemeralRtsHits
from truthexpiry.services.rts_sanitizer import sanitize_rts_hits

from adapters.fakes.synthetic_data import (
    ANALYTICS_EXPORT_KEY,
    API_RATE_LIMIT_KEY,
    BILLING_REFUND_KEY,
    DEFAULT_EVIDENCE_REF,
    PLANNED_ONLY_KEY,
    REPORT_EXPORT_KEY,
    TICKET_EVIDENCE_REF,
)


class FakeClaimExtractionPort:
    """Returns predetermined structured claims without calling an LLM."""

    def __init__(
        self, claims_by_query: dict[str, list[ExtractedClaim]] | None = None
    ) -> None:
        self._claims_by_query = claims_by_query or _default_claims_by_query()
        self.extract_calls: list[tuple[str, EphemeralRtsHits]] = []

    def extract_claims(
        self, query: str, hits: EphemeralRtsHits
    ) -> list[ExtractedClaim]:
        self.extract_calls.append((query, hits))
        evidence_refs = sanitize_rts_hits(hits) or (
            DEFAULT_EVIDENCE_REF,
            TICKET_EVIDENCE_REF,
        )
        normalized = query.strip().lower()

        for keyword, claims in self._claims_by_query.items():
            if keyword in normalized:
                return [
                    ExtractedClaim(
                        key=claim.key,
                        stated_value=(
                            infer_report_export_stated_value(normalized)
                            if keyword == "report export"
                            else claim.stated_value
                        ),
                        evidence_refs=evidence_refs,
                        required_scope_fields=claim.required_scope_fields,
                    )
                    for claim in claims
                ]

        return [
            ExtractedClaim(
                key=PLANNED_ONLY_KEY,
                stated_value="enabled",
                evidence_refs=evidence_refs,
                required_scope_fields=("plan", "region"),
            )
        ]


_DISABLED_AVAILABILITY_PHRASES = (
    "not available",
    "not enabled",
    "unavailable",
    "disabled",
    "turned off",
)

_ENABLED_AVAILABILITY_PHRASES = (
    "enabled",
    "available",
    "turned on",
)


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", text) is not None


def infer_report_export_stated_value(normalized_query: str) -> str:
    """Infer enabled/disabled availability from demo report-export query wording."""
    for phrase in _DISABLED_AVAILABILITY_PHRASES:
        if phrase in normalized_query:
            return "disabled"
    if _contains_token(normalized_query, "off"):
        return "disabled"

    for phrase in _ENABLED_AVAILABILITY_PHRASES:
        if phrase in normalized_query:
            return "enabled"
    if _contains_token(normalized_query, "on"):
        return "enabled"

    return "enabled"


def _default_claims_by_query() -> dict[str, list[ExtractedClaim]]:
    return {
        "report export": [
            ExtractedClaim(
                key=REPORT_EXPORT_KEY,
                stated_value="enabled",
                required_scope_fields=("plan", "region"),
            )
        ],
        "rate limit": [
            ExtractedClaim(
                key=API_RATE_LIMIT_KEY,
                stated_value="100",
                required_scope_fields=("plan", "region"),
            )
        ],
        "conflict": [
            ExtractedClaim(
                key=BILLING_REFUND_KEY,
                stated_value="30_days",
                required_scope_fields=("plan", "region"),
            )
        ],
        "analytics export": [
            ExtractedClaim(
                key=ANALYTICS_EXPORT_KEY,
                stated_value="enabled",
                required_scope_fields=("plan", "region"),
            )
        ],
        "planned": [
            ExtractedClaim(
                key=PLANNED_ONLY_KEY,
                stated_value="enabled",
                required_scope_fields=("plan", "region"),
            )
        ],
    }
