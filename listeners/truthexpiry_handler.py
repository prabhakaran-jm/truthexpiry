from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus

from adapters.composition import LiveAdaptersUnavailableError
from truthexpiry.services.pipeline import (
    TruthExpiryPipeline,
    TruthExpiryRequest,
    TruthExpiryResponse,
)

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

    thread_ts = event.get("thread_ts") or event["ts"]
    team_id = event.get("team") or context.team_id or ""
    channel_id = context.channel_id or event.get("channel", "")
    user_id = context.user_id or event.get("user", "")

    set_status(status="Checking claim freshness...", loading_messages=LOADING_MESSAGES)

    try:
        response = pipeline.handle(
            TruthExpiryRequest(
                team_id=team_id,
                user_id=user_id,
                channel_id=channel_id,
                thread_ts=thread_ts,
                query=query,
                action_token=event.get("action_token"),
            )
        )
    except LiveAdaptersUnavailableError as error:
        logger.warning("TruthExpiry pipeline unavailable: %s", error)
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
        logger.exception("TruthExpiry pipeline failed")
        say(
            text=":warning: Something went wrong while validating claims.",
            thread_ts=thread_ts,
        )
        return

    _render_response(response, say_stream=say_stream)


def _render_response(response: TruthExpiryResponse, *, say_stream: SayStream) -> None:
    streamer = say_stream()
    streamer.append(markdown_text=response.markdown_text)
    streamer.stop(blocks=build_feedback_blocks())
