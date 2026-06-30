from logging import Logger
import time

from slack_bolt import BoltContext, Say, SayStream, SetStatus

from adapters.composition import LiveAdaptersUnavailableError
from truthexpiry.ops.context import (
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from truthexpiry.ops.metrics import metrics_or_noop
from truthexpiry.ops.shutdown import get_shutdown_coordinator
from truthexpiry.services.pipeline import (
    TruthExpiryPipeline,
    TruthExpiryRequest,
    TruthExpiryResponse,
)

from listeners.slack_events import action_token_from_event
from listeners.views.feedback_builder import build_feedback_blocks

LOADING_MESSAGES = [
    "Teaching the hamsters to type faster…",
    "Untangling the internet cables…",
    "Consulting the office goldfish…",
    "Polishing up the response just for you…",
    "Convincing the AI to stop overthinking…",
]


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
) -> None:
    """Delegate a user-triggered query to the TruthExpiry pipeline."""

    coordinator = get_shutdown_coordinator()
    if coordinator is not None and not coordinator.begin_request():
        logger.info(
            "Rejected request during shutdown correlation_id=%s",
            get_correlation_id(),
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

    set_status(status="Checking claim freshness...", loading_messages=LOADING_MESSAGES)

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
    except LiveAdaptersUnavailableError as error:
        metrics.increment(
            "requests_total",
            labels={
                "service": "slack-worker",
                "outcome": "failure",
                "failure_category": "config",
            },
        )
        logger.warning(
            "TruthExpiry pipeline unavailable correlation_id=%s error=%s",
            get_correlation_id(),
            error,
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
        metrics.increment(
            "requests_total",
            labels={
                "service": "slack-worker",
                "outcome": "failure",
                "failure_category": "internal",
            },
        )
        logger.exception(
            "TruthExpiry pipeline failed correlation_id=%s query_length=%d",
            get_correlation_id(),
            len(query),
        )
        say(
            text=":warning: Something went wrong while validating claims.",
            thread_ts=thread_ts,
        )
        return

    metrics.increment(
        "requests_total",
        labels={"service": "slack-worker", "outcome": "success"},
    )
    metrics.observe_duration(
        "request_duration_seconds",
        time.monotonic() - started,
    )
    _render_response(response, say_stream=say_stream)


def _render_response(response: TruthExpiryResponse, *, say_stream: SayStream) -> None:
    streamer = say_stream()
    streamer.append(markdown_text=response.markdown_text)
    streamer.stop(blocks=build_feedback_blocks())
