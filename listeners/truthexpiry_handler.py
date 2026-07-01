from logging import Logger
import time

from slack_bolt import BoltContext, Say, SayStream, SetStatus

from adapters.composition import LiveAdaptersUnavailableError
from truthexpiry.ops.context import (
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from truthexpiry.ops.event_dedup import get_event_dedup_cache
from truthexpiry.ops.metrics import metrics_or_noop
from truthexpiry.ops.shutdown import get_shutdown_coordinator
from truthexpiry.services.pipeline import (
    EXTRACTION_UNAVAILABLE_MESSAGE,
    RTS_UNAVAILABLE_MESSAGE,
    TruthExpiryPipeline,
    TruthExpiryRequest,
    TruthExpiryResponse,
)

from listeners.slack_events import action_token_from_event
from listeners.status_copy import ASSISTANT_LOADING_MESSAGES, ASSISTANT_STATUS
from listeners.views.feedback_builder import build_feedback_blocks
from listeners.views.verdict_builder import build_response_blocks


def run_truthexpiry_query(
    *,
    pipeline: TruthExpiryPipeline,
    context: BoltContext,
    event: dict,
    query: str,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
    event_id: str | None = None,
) -> None:
    """Delegate a user-triggered query to the TruthExpiry pipeline."""

    dedup_cache = get_event_dedup_cache()
    if dedup_cache is not None and event_id is not None:
        if dedup_cache.is_duplicate(event_id):
            logger.info(
                "Ignoring duplicate Slack event",
                extra={
                    "event": "truthexpiry_request_duplicate",
                    "outcome": "skipped",
                },
            )
            return

    coordinator = get_shutdown_coordinator()
    if coordinator is not None and not coordinator.begin_request():
        logger.info(
            "Rejected request during shutdown",
            extra={
                "event": "truthexpiry_request_rejected",
                "outcome": "failure",
                "failure_category": "shutdown",
            },
        )
        return

    correlation_token = set_correlation_id(new_correlation_id())
    try:
        _run_truthexpiry_query_inner(
            pipeline=pipeline,
            context=context,
            event=event,
            query=query,
            logger=logger,
            say=say,
            say_stream=say_stream,
            set_status=set_status,
        )
    finally:
        if coordinator is not None:
            coordinator.end_request()
        reset_correlation_id(correlation_token)


def _run_truthexpiry_query_inner(
    *,
    pipeline: TruthExpiryPipeline,
    context: BoltContext,
    event: dict,
    query: str,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
) -> None:
    thread_ts = event.get("thread_ts") or event["ts"]
    team_id = event.get("team") or context.team_id or ""
    channel_id = context.channel_id or event.get("channel", "")
    user_id = context.user_id or event.get("user", "")

    set_status(
        status=ASSISTANT_STATUS,
        loading_messages=list(ASSISTANT_LOADING_MESSAGES),
    )

    metrics = metrics_or_noop()
    started = time.monotonic()
    try:
        response = pipeline.handle(
            TruthExpiryRequest(
                team_id=team_id,
                user_id=user_id,
                channel_id=channel_id,
                thread_ts=thread_ts,
                query=query,
                action_token=action_token_from_event(event),
            )
        )
    except LiveAdaptersUnavailableError:
        duration_ms = int((time.monotonic() - started) * 1000)
        metrics.increment(
            "requests_total",
            labels={"outcome": "failure", "failure_category": "config"},
        )
        logger.warning(
            "TruthExpiry pipeline unavailable",
            extra={
                "event": "truthexpiry_request",
                "outcome": "failure",
                "failure_category": "config",
                "duration_ms": duration_ms,
                "query_length": len(query),
            },
        )
        say(
            text=(
                ":warning: TruthExpiry is not configured for live adapters yet. "
                "Set `TRUTH_EXPIRY_USE_FAKES=1` for all-fake local mode, or provide "
                "a Slack client and `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` for Milestone 2."
            ),
            thread_ts=thread_ts,
        )
        return
    except Exception:
        duration_ms = int((time.monotonic() - started) * 1000)
        metrics.increment(
            "requests_total",
            labels={"outcome": "failure", "failure_category": "internal"},
        )
        logger.exception(
            "TruthExpiry pipeline failed",
            extra={
                "event": "truthexpiry_request",
                "outcome": "failure",
                "failure_category": "internal",
                "duration_ms": duration_ms,
                "query_length": len(query),
            },
        )
        say(
            text=":warning: Something went wrong while validating claims.",
            thread_ts=thread_ts,
        )
        return

    elapsed = time.monotonic() - started
    duration_ms = int(elapsed * 1000)
    outcome = _response_outcome(response)
    claim_count = len(response.results)
    evidence_count = _evidence_count(response)
    metrics.increment("requests_total", labels={"outcome": outcome})
    metrics.observe_duration("request_duration_seconds", elapsed)
    logger.info(
        "TruthExpiry request completed",
        extra={
            "event": "truthexpiry_request",
            "outcome": outcome,
            "duration_ms": duration_ms,
            "query_length": len(query),
            "claim_count": claim_count,
            "evidence_count": evidence_count,
        },
    )
    _render_response(response, query=query, say_stream=say_stream)


def _response_outcome(response: TruthExpiryResponse) -> str:
    if RTS_UNAVAILABLE_MESSAGE in response.markdown_text:
        return "unavailable"
    if EXTRACTION_UNAVAILABLE_MESSAGE in response.markdown_text:
        return "unavailable"
    return "success"


def _evidence_count(response: TruthExpiryResponse) -> int:
    total = 0
    for result in response.results:
        total += len(result.evidence_refs)
        total += len(result.lifecycle_record_ids)
    return total


def _stream_fallback_text(response: TruthExpiryResponse) -> str:
    if response.results:
        if len(response.results) == 1:
            return f"TruthExpiry: {response.results[0].status.value}"
        return f"TruthExpiry: validated {len(response.results)} claims"
    return "TruthExpiry could not extract a structured claim to validate."


def _render_response(
    response: TruthExpiryResponse,
    *,
    query: str,
    say_stream: SayStream,
) -> None:
    streamer = say_stream()
    blocks = build_response_blocks(query=query, response=response)
    streamer.append(markdown_text=_stream_fallback_text(response))
    streamer.stop(blocks=blocks + build_feedback_blocks())
