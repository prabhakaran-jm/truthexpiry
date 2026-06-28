from dataclasses import dataclass

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.models.verdict import ClaimStatus, OwnerConfirmation, ValidationResult
from truthexpiry.ports.clock import ClockPort
from truthexpiry.ports.lifecycle import LifecycleEvidencePort, LifecycleEvidenceUnavailableError
from truthexpiry.ports.llm import ClaimExtractionPort
from truthexpiry.ports.rts import RtsPort
from truthexpiry.services.clock import as_clock
from truthexpiry.services.labeler import label_claim
from truthexpiry.services.search_plan import build_rts_search_request


@dataclass(frozen=True)
class TruthExpiryRequest:
    team_id: str
    user_id: str
    channel_id: str
    thread_ts: str
    query: str
    action_token: str | None = None
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
        capabilities = self._rts.search_capabilities(request.team_id)
        search_request = build_rts_search_request(
            team_id=request.team_id,
            query=request.query,
            action_token=request.action_token,
            capabilities=capabilities,
        )
        ephemeral_hits = self._rts.search_context(search_request)
        extracted_claims = self._llm.extract_claims(request.query, ephemeral_hits)

        on_date = self._clock.today()
        results: list[ValidationResult] = []
        for claim in extracted_claims:
            try:
                records = self._lifecycle.fetch_records(claim.key)
            except LifecycleEvidenceUnavailableError:
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

        markdown = format_validation_results(request.query, tuple(results))
        return TruthExpiryResponse(markdown_text=markdown, results=tuple(results))


def _unverified_unavailable_result(claim: ExtractedClaim) -> ValidationResult:
    return ValidationResult(
        key=claim.key,
        status=ClaimStatus.UNVERIFIED,
        explanation=(
            "UNVERIFIED — authoritative lifecycle evidence is currently unavailable."
        ),
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
        return (
            f'*Query:* "{query}"\n\n'
            "No structured claims were extracted. TruthExpiry requires deterministic "
            "lifecycle evidence before assigning a status."
        )

    lines = [f'*Query:* "{query}"', ""]
    for result in results:
        lines.append(f"*{result.key.canonical()}* — `{result.status.value}`")
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
