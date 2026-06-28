import os

from adapters.fakes.lifecycle import FakeLifecycleEvidenceAdapter
from adapters.fakes.llm import FakeClaimExtractionPort
from adapters.fakes.rts import FakeRtsPort
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
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
    lifecycle: FakeLifecycleEvidenceAdapter | LifecycleMcpAdapter | None = None,
    llm: FakeClaimExtractionPort | None = None,
    lifecycle_mcp_url: str | None = None,
) -> TruthExpiryPipeline:
    if use_fakes is None:
        use_fakes = os.environ.get("TRUTH_EXPIRY_USE_FAKES", "").strip() == "1"

    if use_fakes:
        return TruthExpiryPipeline(
            rts=rts or FakeRtsPort(),
            lifecycle=lifecycle or FakeLifecycleEvidenceAdapter(),
            llm=llm or FakeClaimExtractionPort(),
            clock=clock or SystemClock(),
        )

    mcp_url = (
        lifecycle_mcp_url
        or os.environ.get("TRUTH_EXPIRY_LIFECYCLE_MCP_URL", "").strip()
    )
    if not mcp_url:
        raise LiveAdaptersUnavailableError(
            "Milestone 1 requires TRUTH_EXPIRY_LIFECYCLE_MCP_URL when "
            "TRUTH_EXPIRY_USE_FAKES is unset. Start the lifecycle MCP server "
            "locally or set TRUTH_EXPIRY_USE_FAKES=1 for all-fake mode."
        )

    return TruthExpiryPipeline(
        rts=rts or FakeRtsPort(),
        lifecycle=lifecycle or LifecycleMcpAdapter(mcp_url),
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
