from dataclasses import dataclass, field
import time

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.models.verdict import ClaimStatus, OwnerConfirmation, ValidationResult
from truthexpiry.ports.clock import ClockPort
from truthexpiry.ports.lifecycle import (
    LifecycleEvidencePort,
    LifecycleEvidenceUnavailableError,
)
from truthexpiry.ports.llm import ClaimExtractionPort, ClaimExtractionUnavailableError
from truthexpiry.ports.rts import RtsPort, RtsSearchUnavailableError
from truthexpiry.ops.metrics import metrics_or_noop
from truthexpiry.services.clock import as_clock
from truthexpiry.services.demo_guidance import format_no_claim_guidance
from truthexpiry.services.labeler import label_claim
from truthexpiry.services.search_plan import build_rts_search_request

EMPTY_RTS_MESSAGE = "No relevant public Slack messages were found."
RTS_UNAVAILABLE_MESSAGE = "Live Slack search is currently unavailable for this request."
EXTRACTION_UNAVAILABLE_MESSAGE = (
    "Claim extraction is temporarily unavailable for this request."
)


@dataclass(frozen=True)
class TruthExpiryRequest:
    team_id: str
    user_id: str
    channel_id: str
    thread_ts: str
    query: str
    action_token: str | None = field(default=None, repr=False)
    owner_confirmations: tuple[OwnerConfirmation, ...] = ()
    entity_owners: dict[str, str] | None = None


@dataclass(frozen=True)
class TruthExpiryResponse:
    markdown_text: str
    results: tuple[ValidationResult, ...]


class TruthExpiryPipeline:
    """Orchestrates RTS discovery, claim extraction, and deterministic labeling."""

    def __init__(
        self,
        *,
        rts: RtsPort,
        lifecycle: LifecycleEvidencePort,
        llm: ClaimExtractionPort,
        clock: ClockPort | None = None,
    ) -> None:
        self._rts = rts
        self._lifecycle = lifecycle
        self._llm = llm
        self._clock = as_clock(clock)

    def handle(self, request: TruthExpiryRequest) -> TruthExpiryResponse:
        metrics = metrics_or_noop()
        search_request = build_rts_search_request(
            team_id=request.team_id,
            query=request.query,
            action_token=request.action_token,
            disable_semantic_search=False,
        )
        rts_started = time.monotonic()
        try:
            ephemeral_hits = self._rts.search_context(search_request)
        except RtsSearchUnavailableError:
            metrics.increment("rts_failures_total", labels={})
            metrics.observe_stage_duration(
                "rts_duration_seconds", time.monotonic() - rts_started
            )
            return TruthExpiryResponse(
                markdown_text=_format_rts_unavailable(request.query),
                results=(),
            )
        metrics.observe_stage_duration(
            "rts_duration_seconds", time.monotonic() - rts_started
        )

        if not ephemeral_hits.hits:
            return TruthExpiryResponse(
                markdown_text=_format_empty_rts(request.query),
                results=(),
            )

        extraction_started = time.monotonic()
        try:
            extracted_claims = self._llm.extract_claims(request.query, ephemeral_hits)
        except ClaimExtractionUnavailableError:
            metrics.increment("extraction_failures_total", labels={})
            metrics.observe_stage_duration(
                "extraction_duration_seconds",
                time.monotonic() - extraction_started,
            )
            return TruthExpiryResponse(
                markdown_text=_format_extraction_unavailable(request.query),
                results=(),
            )
        metrics.observe_stage_duration(
            "extraction_duration_seconds", time.monotonic() - extraction_started
        )

        on_date = self._clock.today()
        results: list[ValidationResult] = []
        lifecycle_started = time.monotonic()
        for claim in extracted_claims:
            try:
                records = self._lifecycle.fetch_records(claim.key)
            except LifecycleEvidenceUnavailableError:
                metrics.increment("lifecycle_failures_total", labels={})
                results.append(_unverified_unavailable_result(claim))
                continue
            results.append(
                label_claim(
                    claim,
                    records,
                    on_date=on_date,
                    owner_confirmations=request.owner_confirmations,
                    entity_owners=request.entity_owners,
                )
            )
        if extracted_claims:
            metrics.observe_stage_duration(
                "lifecycle_duration_seconds", time.monotonic() - lifecycle_started
            )

        markdown = format_validation_results(request.query, tuple(results))
        return TruthExpiryResponse(markdown_text=markdown, results=tuple(results))


def _format_empty_rts(query: str) -> str:
    return f'*Query:* "{query}"\n\n{EMPTY_RTS_MESSAGE}'


def _format_rts_unavailable(query: str) -> str:
    return f'*Query:* "{query}"\n\n{RTS_UNAVAILABLE_MESSAGE}'


def _format_extraction_unavailable(query: str) -> str:
    return f'*Query:* "{query}"\n\n{EXTRACTION_UNAVAILABLE_MESSAGE}'


def _unverified_unavailable_result(claim: ExtractedClaim) -> ValidationResult:
    return ValidationResult(
        key=claim.key,
        status=ClaimStatus.UNVERIFIED,
        explanation=(
            "UNVERIFIED — authoritative lifecycle evidence is currently unavailable."
        ),
        stated_value=claim.stated_value,
        evidence_refs=claim.evidence_refs,
    )


def _format_lifecycle_evidence(record_ids: tuple[str, ...]) -> list[str]:
    if not record_ids:
        return []
    lines = ["Lifecycle evidence:"]
    lines.extend(f"- {record_id}" for record_id in record_ids)
    return lines


def format_validation_results(query: str, results: tuple[ValidationResult, ...]) -> str:
    if not results:
        return format_no_claim_guidance(query)

    lines = [f'*Query:* "{query}"', ""]
    for result in results:
        lines.append(f"*{result.key.canonical()}* — `{result.status.value}`")
        if result.stated_value:
            lines.append(f"*Stated in Slack:* `{result.stated_value}`")
        lines.append(result.explanation)
        if result.evidence_refs:
            source_links = ", ".join(
                f"<{ref.value}|source>"
                for ref in result.evidence_refs
                if ref.ref_type == "slack_permalink"
            )
            if source_links:
                lines.append(f"Sources: {source_links}")
        lines.extend(_format_lifecycle_evidence(result.lifecycle_record_ids))
        if result.user_confirmed:
            lines.append(
                "_Owner confirmed (metadata only; does not override shipped evidence)._"
            )
        lines.append("")

    lines.append(
        "_Statuses are assigned by deterministic rules. The LLM extracts claims only; "
        "it does not decide validity._"
    )
    return "\n".join(lines).strip()
