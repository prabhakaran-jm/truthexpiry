from __future__ import annotations

from adapters.llm.contracts import ClaimExtractionOutputDto, ExtractedClaimDto


class FakeExtractionRunner:
    """Deterministic extraction runner for unit tests."""

    def __init__(
        self,
        *,
        output: ClaimExtractionOutputDto | None = None,
        error: Exception | None = None,
    ) -> None:
        self._output = output or ClaimExtractionOutputDto(claim=None)
        self._error = error
        self.call_count = 0
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def run(self, *, system_prompt: str, user_prompt: str) -> ClaimExtractionOutputDto:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        if self._error is not None:
            raise self._error
        return self._output


def make_claim_output(
    *,
    entity: str = "report_export",
    attribute: str = "availability",
    scope: dict[str, str] | None = None,
    stated_value: str = "enabled",
    evidence_ids: list[str] | None = None,
) -> ClaimExtractionOutputDto:
    return ClaimExtractionOutputDto(
        claim=ExtractedClaimDto(
            entity=entity,
            attribute=attribute,
            scope=scope or {"plan": "starter", "region": "global"},
            stated_value=stated_value,
            evidence_ids=evidence_ids or ["evidence-1"],
        )
    )
