import os

from adapters.fakes.lifecycle import FakeLifecycleEvidenceAdapter
from adapters.fakes.llm import FakeClaimExtractionPort
from adapters.fakes.rts import FakeRtsPort
from truthexpiry.ports.clock import ClockPort
from truthexpiry.services.clock import SystemClock
from truthexpiry.services.pipeline import TruthExpiryPipeline

_pipeline: TruthExpiryPipeline | None = None


class LiveAdaptersUnavailableError(RuntimeError):
    """Raised when production configuration requests unavailable live adapters."""


def build_pipeline(
    *,
    use_fakes: bool | None = None,
    clock: ClockPort | None = None,
    rts: FakeRtsPort | None = None,
    lifecycle: FakeLifecycleEvidenceAdapter | None = None,
    llm: FakeClaimExtractionPort | None = None,
) -> TruthExpiryPipeline:
    if use_fakes is None:
        use_fakes = os.environ.get("TRUTH_EXPIRY_USE_FAKES", "").strip() == "1"

    if not use_fakes:
        raise LiveAdaptersUnavailableError(
            "Live Slack RTS, lifecycle MCP, and LLM adapters are not available in "
            "Milestone 0. Set TRUTH_EXPIRY_USE_FAKES=1 for local fake mode."
        )

    return TruthExpiryPipeline(
        rts=rts or FakeRtsPort(),
        lifecycle=lifecycle or FakeLifecycleEvidenceAdapter(),
        llm=llm or FakeClaimExtractionPort(),
        clock=clock or SystemClock(),
    )


def get_pipeline() -> TruthExpiryPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def reset_pipeline() -> None:
    global _pipeline
    _pipeline = None
