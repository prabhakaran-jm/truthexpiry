import os

from slack_sdk import WebClient

from adapters.fakes.lifecycle import FakeLifecycleEvidenceAdapter
from adapters.fakes.llm import FakeClaimExtractionPort
from adapters.fakes.rts import FakeRtsPort
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
from adapters.slack_rts.adapter import SlackRtsAdapter
from truthexpiry.ports.clock import ClockPort
from truthexpiry.ports.llm import ClaimExtractionPort
from truthexpiry.ports.rts import RtsPort
from truthexpiry.services.clock import SystemClock
from truthexpiry.services.pipeline import TruthExpiryPipeline

_pipeline: TruthExpiryPipeline | None = None

_VALID_CLAIM_EXTRACTORS = frozenset({"fake", "live"})


class LiveAdaptersUnavailableError(RuntimeError):
    """Raised when production configuration requests unavailable live adapters."""


def _resolve_claim_extractor(
    *,
    llm: ClaimExtractionPort | None,
    use_fakes: bool,
) -> ClaimExtractionPort:
    if llm is not None:
        return llm

    if use_fakes:
        return FakeClaimExtractionPort()

    selector = os.environ.get("TRUTH_EXPIRY_CLAIM_EXTRACTOR", "").strip().lower()
    if not selector:
        return FakeClaimExtractionPort()

    if selector not in _VALID_CLAIM_EXTRACTORS:
        raise LiveAdaptersUnavailableError(
            "TRUTH_EXPIRY_CLAIM_EXTRACTOR must be 'fake' or 'live' when set."
        )

    if selector == "fake":
        return FakeClaimExtractionPort()

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not openai_key:
        raise LiveAdaptersUnavailableError(
            "TRUTH_EXPIRY_CLAIM_EXTRACTOR=live requires a non-blank OPENAI_API_KEY."
        )
    return PydanticAiClaimExtractionAdapter()


def build_pipeline(
    *,
    use_fakes: bool | None = None,
    slack_client: WebClient | None = None,
    clock: ClockPort | None = None,
    rts: RtsPort | None = None,
    lifecycle: FakeLifecycleEvidenceAdapter | LifecycleMcpAdapter | None = None,
    llm: ClaimExtractionPort | None = None,
    lifecycle_mcp_url: str | None = None,
) -> TruthExpiryPipeline:
    if use_fakes is None:
        use_fakes = os.environ.get("TRUTH_EXPIRY_USE_FAKES", "").strip() == "1"

    claim_extractor = _resolve_claim_extractor(llm=llm, use_fakes=use_fakes)

    if use_fakes:
        return TruthExpiryPipeline(
            rts=rts or FakeRtsPort(),
            lifecycle=lifecycle or FakeLifecycleEvidenceAdapter(),
            llm=claim_extractor,
            clock=clock or SystemClock(),
        )

    mcp_url = (
        lifecycle_mcp_url
        or os.environ.get("TRUTH_EXPIRY_LIFECYCLE_MCP_URL", "").strip()
    )
    if not mcp_url:
        raise LiveAdaptersUnavailableError(
            "Milestone 2 requires TRUTH_EXPIRY_LIFECYCLE_MCP_URL when "
            "TRUTH_EXPIRY_USE_FAKES is unset. Start the lifecycle MCP server "
            "locally or set TRUTH_EXPIRY_USE_FAKES=1 for all-fake mode."
        )

    if slack_client is None:
        raise LiveAdaptersUnavailableError(
            "Milestone 2 requires an injected Slack WebClient when "
            "TRUTH_EXPIRY_USE_FAKES is unset. Start the app via app.py so Bolt "
            "can provide app.client."
        )

    return TruthExpiryPipeline(
        rts=rts or SlackRtsAdapter(slack_client),
        lifecycle=lifecycle or LifecycleMcpAdapter(mcp_url),
        llm=claim_extractor,
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
