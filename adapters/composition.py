from slack_sdk import WebClient

from adapters.fakes.lifecycle import FakeLifecycleEvidenceAdapter
from adapters.fakes.llm import FakeClaimExtractionPort
from adapters.fakes.rts import FakeRtsPort
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
from adapters.slack_rts.adapter import SlackRtsAdapter
from truthexpiry.config import ConfigError, SlackWorkerSettings
from truthexpiry.ports.clock import ClockPort
from truthexpiry.ports.llm import ClaimExtractionPort
from truthexpiry.ports.rts import RtsPort
from truthexpiry.services.clock import SystemClock
from truthexpiry.services.pipeline import TruthExpiryPipeline

_pipeline: TruthExpiryPipeline | None = None


class LiveAdaptersUnavailableError(RuntimeError):
    """Raised when production configuration requests unavailable live adapters."""


def _config_error_to_live_unavailable(exc: ConfigError) -> LiveAdaptersUnavailableError:
    return LiveAdaptersUnavailableError(str(exc))


def _resolve_settings(
    settings: SlackWorkerSettings | None,
) -> SlackWorkerSettings:
    try:
        return settings if settings is not None else SlackWorkerSettings.from_env()
    except ConfigError as exc:
        raise _config_error_to_live_unavailable(exc) from exc


def _resolve_claim_extractor(
    *,
    settings: SlackWorkerSettings,
    llm: ClaimExtractionPort | None,
    use_fakes: bool,
) -> ClaimExtractionPort:
    if llm is not None:
        return llm

    if use_fakes:
        return FakeClaimExtractionPort()

    if settings.claim_extractor == "fake":
        return FakeClaimExtractionPort()

    if settings.openai_api_key is None:
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
    settings: SlackWorkerSettings | None = None,
) -> TruthExpiryPipeline:
    resolved_settings = _resolve_settings(settings)

    if use_fakes is None:
        use_fakes = resolved_settings.use_fakes

    try:
        resolved_settings.validate_for_composition(
            use_fakes=use_fakes,
            llm_injected=llm is not None,
            lifecycle_injected=lifecycle is not None,
            lifecycle_mcp_url=lifecycle_mcp_url,
        )
    except ConfigError as exc:
        raise _config_error_to_live_unavailable(exc) from exc

    try:
        claim_extractor = _resolve_claim_extractor(
            settings=resolved_settings,
            llm=llm,
            use_fakes=use_fakes,
        )
    except LiveAdaptersUnavailableError:
        raise

    if use_fakes:
        return TruthExpiryPipeline(
            rts=rts or FakeRtsPort(),
            lifecycle=lifecycle or FakeLifecycleEvidenceAdapter(),
            llm=claim_extractor,
            clock=clock or SystemClock(),
        )

    mcp_url = lifecycle_mcp_url or resolved_settings.lifecycle_mcp_url
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

    auth_token = (
        resolved_settings.lifecycle_mcp_auth_token.get_secret()
        if resolved_settings.lifecycle_mcp_auth_token is not None
        else None
    )

    return TruthExpiryPipeline(
        rts=rts or SlackRtsAdapter(slack_client),
        lifecycle=lifecycle or LifecycleMcpAdapter(mcp_url, auth_token=auth_token),
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
